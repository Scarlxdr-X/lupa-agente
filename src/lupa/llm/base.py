"""Interfaz común para cualquier LLM con function calling.

El ciclo del agente (fase 3) solo conoce estas clases. Cada proveedor
(Gemini, Groq...) traduce entre este formato y el de su propia API, de modo
que cambiar de modelo es cambiar una variable en el .env.

Flujo de una vuelta del ciclo:
    1. El agente envía el historial (lista de `Mensaje`) y las tools disponibles.
    2. El proveedor responde con una `RespuestaLLM`: texto, llamadas a tools, o ambos.
    3. Si hay llamadas, el agente ejecuta cada tool y agrega un `Mensaje` con
       rol "tool" por cada resultado. Luego vuelve al paso 1.
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, TypeVar

log = logging.getLogger(__name__)

Rol = Literal["usuario", "asistente", "tool"]
T = TypeVar("T")


# ---------------------------------------------------------------------------
# Tipos de datos
# ---------------------------------------------------------------------------


@dataclass
class DefinicionTool:
    """Describe una tool para el LLM: nombre, para qué sirve y qué argumentos recibe.

    `parametros` es un JSON Schema de tipo "object", por ejemplo:
        {"type": "object",
         "properties": {"consulta": {"type": "string", "description": "..."}},
         "required": ["consulta"]}
    """

    nombre: str
    descripcion: str
    parametros: dict[str, Any]


@dataclass
class LlamadaTool:
    """Una petición del LLM para ejecutar una tool con ciertos argumentos."""

    id: str
    nombre: str
    argumentos: dict[str, Any]


def nuevo_id_llamada() -> str:
    """Id para llamadas que el proveedor no identificó. El prefijo `lupa-` lo
    marca como generado localmente, para no reenviarlo a la API."""
    return f"lupa-{uuid.uuid4().hex[:8]}"


@dataclass
class Mensaje:
    """Un mensaje del historial de conversación.

    - rol "usuario":   `texto` es la pregunta.
    - rol "asistente": `texto` y/o `llamadas` (las tools que el LLM pidió).
    - rol "tool":      `texto` es el resultado; `id_llamada` y `nombre_tool`
                        indican a qué llamada responde.

    `nativo` guarda la respuesta original del proveedor. Gemini 3 exige que se
    le devuelva tal cual (con sus "firmas de pensamiento") en el siguiente
    turno; si se reconstruye a mano, la API responde con error 400.
    """

    rol: Rol
    texto: str = ""
    llamadas: list[LlamadaTool] = field(default_factory=list)
    id_llamada: str | None = None
    nombre_tool: str | None = None
    nativo: Any = None
    proveedor: str | None = None

    @classmethod
    def usuario(cls, texto: str) -> "Mensaje":
        return cls(rol="usuario", texto=texto)

    @classmethod
    def resultado_tool(cls, llamada: LlamadaTool, resultado: str) -> "Mensaje":
        return cls(rol="tool", texto=resultado, id_llamada=llamada.id, nombre_tool=llamada.nombre)


@dataclass
class Uso:
    """Tokens consumidos en una llamada al LLM (para medir costo en la evaluación)."""

    tokens_entrada: int = 0
    tokens_salida: int = 0


@dataclass
class RespuestaLLM:
    """Lo que devuelve un proveedor después de una llamada."""

    mensaje: Mensaje
    uso: Uso
    motivo_fin: str | None = None
    duracion_s: float = 0.0

    @property
    def texto(self) -> str:
        return self.mensaje.texto

    @property
    def llamadas(self) -> list[LlamadaTool]:
        return self.mensaje.llamadas

    @property
    def pide_tools(self) -> bool:
        return bool(self.mensaje.llamadas)


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------


class ErrorLLM(RuntimeError):
    """Fallo al llamar al LLM que no se resolvió con reintentos."""


class ErrorConfiguracion(ErrorLLM):
    """Falta una clave o un parámetro para crear el proveedor."""


# ---------------------------------------------------------------------------
# Reintentos
# ---------------------------------------------------------------------------


def con_reintentos(
    funcion: Callable[[], T],
    es_reintentable: Callable[[Exception], bool],
    max_reintentos: int = 4,
    espera_inicial: float = 2.0,
    dormir: Callable[[float], None] = time.sleep,
) -> T:
    """Ejecuta `funcion`; si falla con un error temporal, espera y la repite.

    La espera se duplica en cada intento (2 s, 4 s, 8 s...) con un poco de azar
    para no chocar con otros clientes. Útil sobre todo para el error 429 de las
    capas gratuitas, que se limitan por peticiones por minuto.
    """
    intento = 0
    while True:
        try:
            return funcion()
        except Exception as exc:  # noqa: BLE001 - se filtra con es_reintentable
            if intento >= max_reintentos or not es_reintentable(exc):
                raise
            espera = espera_inicial * (2**intento) * (1 + random.random() * 0.25)
            log.warning("Error temporal del LLM (%s). Reintento %d en %.1f s", exc, intento + 1, espera)
            dormir(espera)
            intento += 1


# ---------------------------------------------------------------------------
# Proveedor abstracto
# ---------------------------------------------------------------------------


class ProveedorLLM(ABC):
    """Base de todos los proveedores. Las subclases implementan `_generar`."""

    #: Identificador corto del proveedor ("gemini", "openai_compat").
    nombre: str = "base"

    def __init__(self, modelo: str, max_reintentos: int = 4, espera_inicial: float = 2.0) -> None:
        self.modelo = modelo
        self.max_reintentos = max_reintentos
        self.espera_inicial = espera_inicial

    def generar(
        self,
        mensajes: list[Mensaje],
        tools: list[DefinicionTool] | None = None,
        sistema: str | None = None,
    ) -> RespuestaLLM:
        """Envía el historial al LLM y devuelve su respuesta normalizada.

        Args:
            mensajes: historial completo, del más antiguo al más reciente.
            tools: tools que el LLM puede pedir en esta vuelta.
            sistema: instrucciones de sistema (rol y reglas del agente).
        """
        inicio = time.perf_counter()
        respuesta = con_reintentos(
            lambda: self._generar(mensajes, tools or [], sistema),
            self._es_reintentable,
            max_reintentos=self.max_reintentos,
            espera_inicial=self.espera_inicial,
        )
        respuesta.duracion_s = time.perf_counter() - inicio
        respuesta.mensaje.proveedor = self.nombre
        return respuesta

    @abstractmethod
    def _generar(
        self, mensajes: list[Mensaje], tools: list[DefinicionTool], sistema: str | None
    ) -> RespuestaLLM:
        """Una sola llamada a la API, sin reintentos."""

    @abstractmethod
    def _es_reintentable(self, error: Exception) -> bool:
        """True si el error es temporal (límite de peticiones, servidor caído...)."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(modelo={self.modelo!r})"
