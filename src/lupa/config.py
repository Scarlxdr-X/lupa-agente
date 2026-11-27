"""Configuración del proyecto.

Las claves y parámetros se buscan en este orden:
    1. Variables de entorno (incluye las que carga el archivo .env).
    2. Secretos de Google Colab (solo si el código corre en Colab).
    3. Valor por defecto.

Así el mismo código funciona en local y en Colab sin cambios.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROVEEDORES_VALIDOS = ("gemini", "openai_compat")

# Modelos de Gemini que se prueban, en orden, si el principal está saturado o sin cuota.
RESPALDO_GEMINI = (
    "gemini-3.5-flash,gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash,"
    "gemini-3.5-flash-lite,gemini-3.1-flash-lite"
)


def _secreto_de_colab(nombre: str) -> str | None:
    """Devuelve un secreto de Colab, o None si no estamos en Colab o no existe."""
    try:
        from google.colab import userdata  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        return userdata.get(nombre)
    except Exception:  # SecretNotFoundError, NotebookAccessError, etc.
        return None


def obtener_valor(nombre: str, defecto: str | None = None) -> str | None:
    """Busca `nombre` en el entorno, luego en Colab; si no aparece, usa `defecto`.

    Un valor vacío (por ejemplo `GROQ_API_KEY=` en el .env) cuenta como ausente.
    """
    valor = os.environ.get(nombre)
    if valor:
        return valor.strip()
    valor = _secreto_de_colab(nombre)
    if valor:
        return valor.strip()
    return defecto


@dataclass(frozen=True)
class Config:
    """Parámetros del agente. Se crea con `Config.cargar()`."""

    proveedor: str
    gemini_api_key: str | None
    modelo_gemini: str
    openai_api_key: str | None
    openai_base_url: str
    modelo_openai: str
    tavily_api_key: str | None
    soda_app_token: str | None
    max_pasos: int
    horas_cache: float = 24
    modelos_respaldo_gemini: tuple[str, ...] = ()
    carpeta_cache: str = "cache"
    carpeta_salidas: str = "salidas"

    @classmethod
    def cargar(cls, archivo_env: str | Path | None = None) -> "Config":
        """Lee la configuración. Si se pasa `archivo_env`, carga ese .env primero."""
        # override=False: una variable ya definida en el entorno gana sobre el .env
        load_dotenv(archivo_env, override=False)

        proveedor = (obtener_valor("LUPA_PROVEEDOR", "gemini") or "gemini").lower()
        if proveedor not in PROVEEDORES_VALIDOS:
            raise ValueError(
                f"LUPA_PROVEEDOR='{proveedor}' no es válido. Usa uno de: {', '.join(PROVEEDORES_VALIDOS)}"
            )

        max_pasos_txt = obtener_valor("LUPA_MAX_PASOS", "15") or "15"
        try:
            max_pasos = int(max_pasos_txt)
        except ValueError as exc:
            raise ValueError(f"LUPA_MAX_PASOS debe ser un número entero, no '{max_pasos_txt}'") from exc

        return cls(
            proveedor=proveedor,
            gemini_api_key=obtener_valor("GEMINI_API_KEY") or obtener_valor("GOOGLE_API_KEY"),
            modelo_gemini=obtener_valor("LUPA_MODELO_GEMINI", "gemini-3.8-flash") or "gemini-3.8-flash",
            openai_api_key=obtener_valor("LUPA_OPENAI_API_KEY") or obtener_valor("GROQ_API_KEY"),
            openai_base_url=obtener_valor("LUPA_OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
            or "https://api.groq.com/openai/v1",
            modelo_openai=obtener_valor("LUPA_MODELO_OPENAI", "openai/gpt-oss-120b") or "openai/gpt-oss-120b",
            tavily_api_key=obtener_valor("TAVILY_API_KEY"),
            soda_app_token=obtener_valor("SODA_APP_TOKEN"),
            max_pasos=max_pasos,
            horas_cache=float(obtener_valor("LUPA_CACHE_HORAS", "24") or 24),
            modelos_respaldo_gemini=tuple(
                m.strip()
                for m in (obtener_valor("LUPA_MODELOS_RESPALDO_GEMINI", RESPALDO_GEMINI) or "").split(",")
                if m.strip()
            ),
            carpeta_cache=obtener_valor("LUPA_CARPETA_CACHE", "cache") or "cache",
            carpeta_salidas=obtener_valor("LUPA_CARPETA_SALIDAS", "salidas") or "salidas",
        )

    def resumen(self) -> dict[str, str]:
        """Resumen apto para imprimir: de cada clave muestra solo sus últimos 4 caracteres."""

        def estado(clave: str | None) -> str:
            return f"configurada (…{clave[-4:]})" if clave else "FALTA"

        return {
            "Proveedor activo": self.proveedor,
            "Gemini": f"{estado(self.gemini_api_key)} · modelo {self.modelo_gemini}",
            "Respaldo de Gemini": ", ".join(m for m in self.modelos_respaldo_gemini if m != self.modelo_gemini)
            or "ninguno",
            "Compatible con OpenAI": f"{estado(self.openai_api_key)} · {self.modelo_openai} en {self.openai_base_url}",
            "Tavily": estado(self.tavily_api_key),
            "Token de datos.gov.co": "configurado" if self.soda_app_token else "sin token (opcional)",
            "Máximo de pasos": str(self.max_pasos),
        }
