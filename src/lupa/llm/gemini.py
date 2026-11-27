"""Proveedor para los modelos Gemini, usando el SDK oficial `google-genai`.

Detalles que este módulo resuelve:
    - Desactiva el "function calling automático" del SDK: queremos que el ciclo
      del agente (fase 3) ejecute las tools, no el SDK.
    - Gemini 3 devuelve "firmas de pensamiento" en las llamadas a tools y exige
      recibirlas de vuelta en el siguiente turno (si no, error 400). Por eso
      cada respuesta guarda su `Content` original en `Mensaje.nativo` y se
      reenvía sin modificar.
    - Si el LLM pide varias tools a la vez, todos los resultados deben ir en un
      mismo `Content`; intercalarlos también produce error 400.
    - Modelos de respaldo: si el modelo principal está saturado (503) o sin
      cuota (429), se pasa al siguiente de la lista sin perder la conversación.
      Las firmas solo valen para el modelo que las creó, así que al cambiar de
      modelo se reenvían con el marcador que la documentación de Gemini indica
      para historiales que vienen de otro modelo (`skip_thought_signature_validator`).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import httpx

from google import genai
from google.genai import errors, types

from .base import (
    DefinicionTool,
    ErrorConfiguracion,
    ErrorLLM,
    LlamadaTool,
    Mensaje,
    ProveedorLLM,
    RespuestaLLM,
    Uso,
    nuevo_id_llamada,
)

log = logging.getLogger(__name__)

# Códigos HTTP que indican un problema temporal: límite de peticiones o servidor.
# Con cualquiera de ellos se prueba el siguiente modelo de respaldo.
_CODIGOS_TEMPORALES = {429, 500, 502, 503, 504}

# Firma que Gemini acepta para llamadas a tools que no generó el modelo actual
# (historial que viene de otro modelo). Es el "último recurso" de la documentación.
FIRMA_SIN_VALIDAR = b"skip_thought_signature_validator"

# Si el límite por minuto pide esperar hasta esto, se espera en vez de cambiar de modelo.
_ESPERA_MAXIMA_S = 65


class ErrorCuotaAgotada(ErrorLLM):
    """Todos los modelos de Gemini agotaron su cuota diaria. No se reintenta."""

    def __init__(self, agotados: set[str]) -> None:
        super().__init__(
            "Se agotó la cuota diaria gratuita de todos los modelos de Gemini configurados "
            f"({', '.join(sorted(agotados))}). Se reinicia a la medianoche del Pacífico "
            "(3:00 a. m. en Colombia). Mientras tanto, usa la clave de otro proyecto o activa la facturación."
        )


def tipo_de_limite(error: Exception) -> tuple[str, float | None]:
    """Lee un error 429 de Gemini: ¿cuota diaria o por minuto?, y cuántos segundos pide esperar.

    El mensaje trae el id de la cuota (ej. GenerateRequestsPerDayPerProjectPerModel-FreeTier)
    y una sugerencia como "Please retry in 33.5s" o "retryDelay": "33s".
    """
    texto = str(error)
    espera = re.search(r"retry in ([\d.]+)\s*s", texto, re.IGNORECASE) or re.search(
        r"retryDelay['\"]?\s*:\s*['\"]([\d.]+)s", texto
    )
    segundos = float(espera.group(1)) if espera else None
    tipo = "diaria" if re.search(r"PerDay|per day", texto, re.IGNORECASE) else "minuto"
    return tipo, segundos


class ProveedorGemini(ProveedorLLM):
    nombre = "gemini"

    def __init__(
        self,
        api_key: str | None,
        modelo: str = "gemini-3.8-flash",
        cliente: genai.Client | None = None,
        modelos_respaldo: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(modelo, **kwargs)
        #: Modelo principal seguido de los de respaldo, sin repetidos.
        self.modelos = list(dict.fromkeys([modelo, *(modelos_respaldo or [])]))
        #: Modelos que agotaron su cuota diaria en esta sesión (no se vuelven a intentar).
        self.agotados: set[str] = set()
        self.dormir = time.sleep
        if cliente is None:
            if not api_key:
                raise ErrorConfiguracion(
                    "Falta GEMINI_API_KEY. Créala en https://aistudio.google.com/apikey "
                    "y guárdala en el .env o en los secretos de Colab."
                )
            # Sin esto, el SDK reintenta cada 503 hasta 5 veces (esperando hasta 60 s cada vez)
            # y no tiene tiempo límite: con un modelo saturado la celda parece colgada.
            # Un solo intento y 90 s como máximo; el cambio de modelo lo hace _generar.
            cliente = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=90_000, retry_options=types.HttpRetryOptions(attempts=1)
                ),
            )
        self.cliente = cliente

    # -- llamada a la API ----------------------------------------------------

    def _generar(
        self, mensajes: list[Mensaje], tools: list[DefinicionTool], sistema: str | None
    ) -> RespuestaLLM:
        config = types.GenerateContentConfig(
            system_instruction=sistema,
            tools=[self._a_tool(tools)] if tools else None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        # Primero el modelo actual; luego los de respaldo en orden, saltando los
        # que ya agotaron su cuota diaria en esta sesión.
        candidatos = [m for m in [self.modelo, *self.modelos] if m not in self.agotados]
        candidatos = list(dict.fromkeys(candidatos))
        if not candidatos:
            raise ErrorCuotaAgotada(self.agotados)

        i, ya_espero = 0, False
        while i < len(candidatos):
            modelo = candidatos[i]
            try:
                respuesta = self.cliente.models.generate_content(
                    model=modelo,
                    contents=self.a_contents(mensajes, modelo),
                    config=config,
                )
            except httpx.TransportError as exc:
                # Tiempo límite (90 s) o conexión caída: se trata igual que un modelo saturado.
                siguiente = candidatos[i + 1] if i + 1 < len(candidatos) else None
                if siguiente is None:
                    raise
                log.warning("%s no respondió a tiempo (%s). Pruebo con %s.", modelo, type(exc).__name__, siguiente)
                i, ya_espero = i + 1, False
                continue
            except errors.APIError as exc:
                siguiente = candidatos[i + 1] if i + 1 < len(candidatos) else None
                if exc.code == 404 and siguiente is not None:
                    # Modelo retirado o no disponible para esta clave: se salta para siempre.
                    self.agotados.add(modelo)
                    log.warning("%s no existe para esta clave (error 404). Pruebo con %s.", modelo, siguiente)
                    i, ya_espero = i + 1, False
                    continue
                if exc.code not in _CODIGOS_TEMPORALES:
                    raise
                if exc.code == 429:
                    tipo, segundos = tipo_de_limite(exc)
                    if tipo == "diaria":
                        self.agotados.add(modelo)
                        log.warning("Se agotó la cuota diaria de %s; no lo vuelvo a usar en esta sesión.", modelo)
                        if siguiente is None and len(self.agotados) >= len(self.modelos):
                            raise ErrorCuotaAgotada(self.agotados) from exc
                    elif not ya_espero and segundos is not None and segundos <= _ESPERA_MAXIMA_S:
                        # Límite por minuto: esperar un poco sale más barato que gastar otro modelo.
                        log.warning("%s llegó a su límite por minuto; espero %.0f s y repito.", modelo, segundos + 1)
                        self.dormir(segundos + 1)
                        ya_espero = True
                        continue
                if siguiente is None:
                    raise
                log.warning("%s no está disponible (error %s). Pruebo con %s.", modelo, exc.code, siguiente)
                i, ya_espero = i + 1, False
                continue
            if modelo != self.modelo:
                log.warning("Lupa sigue con el modelo %s (antes %s).", modelo, self.modelo)
                self.modelo = modelo
            return self.desde_respuesta(respuesta, modelo)
        raise AssertionError("inalcanzable")  # pragma: no cover

    def _es_reintentable(self, error: Exception) -> bool:
        if isinstance(error, httpx.TransportError):
            return True
        return isinstance(error, errors.APIError) and error.code in _CODIGOS_TEMPORALES

    def listar_modelos(self) -> list[str]:
        """Modelos que la clave puede usar para generar texto."""
        nombres = []
        for modelo in self.cliente.models.list():
            acciones = getattr(modelo, "supported_actions", None) or []
            if not acciones or "generateContent" in acciones:
                nombres.append(modelo.name.removeprefix("models/"))
        return sorted(nombres)

    # -- traducción: formato de Lupa → formato de Gemini --------------------

    @staticmethod
    def _a_tool(tools: list[DefinicionTool]) -> types.Tool:
        return types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=t.nombre,
                    description=t.descripcion,
                    parameters_json_schema=t.parametros,
                )
                for t in tools
            ]
        )

    def a_contents(self, mensajes: list[Mensaje], modelo: str | None = None) -> list[types.Content]:
        """Convierte el historial de Lupa en la lista `contents` de Gemini.

        `modelo` es el modelo que recibirá la petición (por defecto, el actual):
        las respuestas que produjo otro modelo se reenvían sin sus firmas.
        """
        modelo = modelo or self.modelo
        contents: list[types.Content] = []
        resultados_pendientes: list[types.Part] = []

        def volcar_resultados() -> None:
            # Los resultados consecutivos de tools van juntos en un solo Content.
            if resultados_pendientes:
                contents.append(types.Content(role="user", parts=list(resultados_pendientes)))
                resultados_pendientes.clear()

        for m in mensajes:
            if m.rol == "tool":
                resultados_pendientes.append(self._parte_resultado(m))
                continue

            volcar_resultados()
            if m.rol == "usuario":
                contents.append(types.Content(role="user", parts=[types.Part(text=m.texto)]))
            elif m.rol == "asistente":
                contents.append(self._content_asistente(m, modelo))
            else:  # pragma: no cover - el tipo Rol no permite otros valores
                raise ValueError(f"Rol desconocido: {m.rol}")

        volcar_resultados()
        return contents

    def _content_asistente(self, m: Mensaje, modelo: str) -> types.Content:
        if m.proveedor == self.nombre and isinstance(m.nativo, types.Content):
            # Caso normal: reenviar exactamente lo que devolvió Gemini (con firmas).
            if m.modelo in (None, modelo):
                return m.nativo
            # Lo produjo otro modelo de Gemini (hubo un cambio de respaldo).
            return _sin_firmas_propias(m.nativo)
        # Mensaje de otro proveedor (Groq): se reconstruye con la firma comodín.
        partes: list[types.Part] = []
        if m.texto:
            partes.append(types.Part(text=m.texto))
        for llamada in m.llamadas:
            partes.append(
                types.Part(
                    function_call=types.FunctionCall(
                        id=_id_para_api(llamada.id), name=llamada.nombre, args=llamada.argumentos
                    ),
                    thought_signature=FIRMA_SIN_VALIDAR,
                )
            )
        return types.Content(role="model", parts=partes or [types.Part(text="")])

    @staticmethod
    def _parte_resultado(m: Mensaje) -> types.Part:
        return types.Part(
            function_response=types.FunctionResponse(
                id=_id_para_api(m.id_llamada),
                name=m.nombre_tool,
                response={"resultado": m.texto},
            )
        )

    # -- traducción: respuesta de Gemini → formato de Lupa ------------------

    def desde_respuesta(self, respuesta: types.GenerateContentResponse, modelo: str | None = None) -> RespuestaLLM:
        candidato = respuesta.candidates[0] if respuesta.candidates else None
        content = candidato.content if candidato else None
        partes = (content.parts if content else None) or []

        # El texto visible excluye los "pensamientos" (partes con thought=True).
        texto = "".join(p.text for p in partes if p.text and not p.thought)
        llamadas = [
            LlamadaTool(id=fc.id or nuevo_id_llamada(), nombre=fc.name or "", argumentos=dict(fc.args or {}))
            for fc in (respuesta.function_calls or [])
        ]

        meta = respuesta.usage_metadata
        uso = Uso(
            tokens_entrada=(meta.prompt_token_count or 0) if meta else 0,
            # Los tokens de pensamiento se cobran como salida.
            tokens_salida=((meta.candidates_token_count or 0) + (meta.thoughts_token_count or 0)) if meta else 0,
        )
        motivo = None
        if candidato and candidato.finish_reason is not None:
            motivo = getattr(candidato.finish_reason, "value", str(candidato.finish_reason))

        return RespuestaLLM(
            mensaje=Mensaje(
                rol="asistente",
                texto=texto,
                llamadas=llamadas,
                nativo=content,
                proveedor=self.nombre,
                modelo=modelo or self.modelo,
            ),
            uso=uso,
            motivo_fin=motivo,
        )


def _sin_firmas_propias(content: types.Content) -> types.Content:
    """Copia de una respuesta de otro modelo de Gemini, apta para el modelo actual.

    Quita los pensamientos y las firmas originales (solo las entiende el modelo
    que las creó) y marca cada llamada a tool con la firma comodín.
    """
    partes = []
    for parte in content.parts or []:
        if parte.thought:
            continue
        copia = parte.model_copy()
        copia.thought_signature = FIRMA_SIN_VALIDAR if copia.function_call else None
        partes.append(copia)
    return types.Content(role=content.role or "model", parts=partes or [types.Part(text="")])


def _id_para_api(id_llamada: str | None) -> str | None:
    """Los ids generados por Lupa (prefijo `lupa-`) no se envían a Gemini."""
    if not id_llamada or id_llamada.startswith("lupa-"):
        return None
    return id_llamada
