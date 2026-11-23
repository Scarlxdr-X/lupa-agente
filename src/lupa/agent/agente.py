"""El ciclo del agente: razonar → actuar → observar.

En cada vuelta:
    1. Razonar:  el LLM recibe la pregunta, el historial y las tools, y decide
                 si responder o pedir una o varias tools.
    2. Actuar:   se ejecuta cada tool pedida (RegistroTools nunca lanza
                 excepciones: los errores vuelven como texto).
    3. Observar: los resultados se agregan al historial y se vuelve al paso 1.

El ciclo termina cuando el LLM responde sin pedir tools, o al llegar al máximo
de pasos (entonces se le pide la mejor respuesta posible con lo que tiene).

`responder_por_pasos` es un generador: entrega cada evento (llamada a una
tool, resultado, respuesta) apenas ocurre, para que la interfaz muestre la
traza en vivo. `responder` es la versión simple que devuelve el resultado final.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from ..config import Config
from ..llm.base import Mensaje, ProveedorLLM
from ..skills import Skill, cargar_skills, catalogo
from ..tools import ClienteSODA, Contexto, Fuente, crear_registro

SISTEMA_BASE = """Eres Lupa, un agente que responde preguntas sobre los datos abiertos de Colombia publicados en datos.gov.co.
Hoy es {fecha}.

Cómo trabajas:
- Razonas paso a paso y actúas con tools. Toda cifra de tu respuesta debe salir de una tool: nunca inventes datos ni hagas cuentas de memoria.
- buscar_datasets encuentra conjuntos y sus columnas; consultar_dataset los consulta (agrega en el servidor con select y group); ejecutar_python analiza tablas y hace gráficas; calculadora hace cuentas exactas; buscar_web da contexto y noticias.
- Si una tool responde ERROR, lee el mensaje, corrige y vuelve a intentar. Si falla dos veces por el mismo camino, cambia de estrategia.
- No consultes ni muestres datos personales. No des recomendaciones financieras ni opiniones políticas.
- Responde en español y en markdown. Cita cada conjunto (nombre, id y enlace https://www.datos.gov.co/d/<id>) y cada página web que uses.
- Si los datos no alcanzan para responder, dilo con claridad."""

SECCION_SKILLS = """

Skills disponibles (procedimientos probados por el equipo). Antes de cada parte de la tarea, carga con cargar_skill el skill que le corresponda y sigue sus pasos; para cerrar una tarea de varios pasos carga redaccion_informe:
{catalogo}"""

NUDGE_RESPUESTA = "Escribe ahora la respuesta final para el usuario, en español."
NUDGE_LIMITE = (
    "Llegaste al límite de pasos. Con la información que ya tienes, escribe la mejor respuesta final posible "
    "y di claramente qué no alcanzaste a verificar."
)


@dataclass
class Evento:
    """Un paso de la traza del agente."""

    tipo: str  # "pensamiento" | "llamada" | "resultado" | "respuesta" | "aviso" | "error"
    paso: int
    texto: str = ""
    tool: str | None = None
    argumentos: dict[str, Any] | None = None
    ok: bool = True
    duracion_s: float = 0.0


@dataclass
class Resultado:
    """Todo lo que produjo el agente al responder una pregunta (lo usan la interfaz y la evaluación)."""

    pregunta: str
    respuesta: str = ""
    eventos: list[Evento] = field(default_factory=list)
    graficas: list[Path] = field(default_factory=list)
    fuentes: list[Fuente] = field(default_factory=list)
    skills_cargados: list[str] = field(default_factory=list)
    pasos: int = 0
    llamadas_llm: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    duracion_s: float = 0.0
    completo: bool = False
    error: str | None = None

    @property
    def tools_usadas(self) -> list[str]:
        return [e.tool for e in self.eventos if e.tipo == "llamada" and e.tool]

    @property
    def errores_tool(self) -> int:
        return sum(1 for e in self.eventos if e.tipo == "resultado" and not e.ok)

    @property
    def errores_recuperados(self) -> int:
        """Errores de una tool seguidos, más adelante, de un uso exitoso de la misma tool."""
        resultados = [e for e in self.eventos if e.tipo == "resultado"]
        recuperados = 0
        for i, e in enumerate(resultados):
            if not e.ok and any(r.ok and r.tool == e.tool for r in resultados[i + 1 :]):
                recuperados += 1
        return recuperados


class Agente:
    """Agente Lupa. Mantiene la memoria de la conversación entre preguntas."""

    def __init__(
        self,
        llm: ProveedorLLM,
        config: Config | None = None,
        usar_skills: bool = True,
        carpeta_skills: Path | None = None,
        carpeta_trabajo: Path | None = None,
        cliente_soda: ClienteSODA | None = None,
        max_pasos: int | None = None,
    ) -> None:
        self.llm = llm
        self.config = config or Config.cargar()
        self.max_pasos = max_pasos or self.config.max_pasos
        self.skills: dict[str, Skill] = cargar_skills(carpeta_skills) if usar_skills else {}

        sesion = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"
        self.contexto = Contexto(Path(carpeta_trabajo or Path(self.config.carpeta_salidas) / sesion))
        self._skills_cargados: list[str] = []
        self.registro = crear_registro(
            self.config, self.contexto, self.skills, cliente_soda, al_cargar_skill=self._skills_cargados.append
        )

        self.sistema = SISTEMA_BASE.format(fecha=f"{datetime.now():%Y-%m-%d}")
        if self.skills:
            self.sistema += SECCION_SKILLS.format(catalogo=catalogo(self.skills))

        # Memoria: solo preguntas y respuestas finales. Los pasos intermedios
        # (resultados de tools) no se arrastran a la siguiente pregunta.
        self.historial: list[Mensaje] = []
        self.ultimo_resultado: Resultado | None = None

    def reiniciar(self) -> None:
        """Olvida la conversación (las tablas y gráficas siguen en la carpeta de trabajo)."""
        self.historial = []

    def responder(self, pregunta: str) -> Resultado:
        for _ in self.responder_por_pasos(pregunta):
            pass
        assert self.ultimo_resultado is not None
        return self.ultimo_resultado

    def responder_por_pasos(self, pregunta: str) -> Iterator[Evento]:
        res = Resultado(pregunta=pregunta)
        self.ultimo_resultado = res
        inicio = time.perf_counter()
        n_graficas, n_fuentes, n_skills = (
            len(self.contexto.graficas),
            len(self.contexto.fuentes),
            len(self._skills_cargados),
        )
        tools = self.registro.definiciones
        mensajes = [*self.historial, Mensaje.usuario(pregunta)]
        respuesta_final: Mensaje | None = None
        ya_insistio = False

        def emitir(evento: Evento) -> Evento:
            res.eventos.append(evento)
            return evento

        try:
            for paso in range(1, self.max_pasos + 1):
                res.pasos = paso
                r = self.llm.generar(mensajes, tools=tools, sistema=self.sistema)
                self._contar(res, r)

                if not r.pide_tools and not r.texto.strip():
                    # Respuesta vacía: se pide la respuesta una vez, sin guardar el mensaje vacío.
                    if ya_insistio:
                        raise RuntimeError("El LLM devolvió dos respuestas vacías seguidas.")
                    ya_insistio = True
                    mensajes.append(Mensaje.usuario(NUDGE_RESPUESTA))
                    yield emitir(Evento("aviso", paso, "Respuesta vacía; se le pide al LLM que responda."))
                    continue

                mensajes.append(r.mensaje)
                if not r.pide_tools:
                    respuesta_final = r.mensaje
                    res.completo = True
                    break

                if r.texto.strip():
                    yield emitir(Evento("pensamiento", paso, r.texto.strip()))
                for llamada in r.llamadas:
                    yield emitir(Evento("llamada", paso, tool=llamada.nombre, argumentos=llamada.argumentos))
                    resultado = self.registro.ejecutar(llamada)
                    mensajes.append(Mensaje.resultado_tool(llamada, resultado.texto))
                    yield emitir(
                        Evento(
                            "resultado",
                            paso,
                            resultado.texto,
                            tool=llamada.nombre,
                            ok=resultado.ok,
                            duracion_s=resultado.duracion_s,
                        )
                    )
            else:
                yield emitir(Evento("aviso", self.max_pasos, f"Se alcanzó el máximo de {self.max_pasos} pasos."))
                mensajes.append(Mensaje.usuario(NUDGE_LIMITE))
                r = self.llm.generar(mensajes, tools=None, sistema=self.sistema)
                self._contar(res, r)
                respuesta_final = r.mensaje

        except Exception as exc:  # noqa: BLE001 - un fallo del LLM no debe tumbar la interfaz
            res.error = f"{type(exc).__name__}: {exc}"
            yield emitir(Evento("error", res.pasos, res.error, ok=False))

        res.respuesta = respuesta_final.texto if respuesta_final else (
            "No pude completar la respuesta por un error al hablar con el modelo de lenguaje. "
            f"Detalle: {res.error}"
        )
        res.graficas = self.contexto.graficas[n_graficas:]
        res.fuentes = self.contexto.fuentes[n_fuentes:]
        res.skills_cargados = self._skills_cargados[n_skills:]
        res.duracion_s = time.perf_counter() - inicio

        if respuesta_final is not None:
            self.historial += [Mensaje.usuario(pregunta), respuesta_final]
        yield emitir(Evento("respuesta", res.pasos, res.respuesta, ok=res.error is None))

    @staticmethod
    def _contar(res: Resultado, r) -> None:
        res.llamadas_llm += 1
        res.tokens_entrada += r.uso.tokens_entrada
        res.tokens_salida += r.uso.tokens_salida
