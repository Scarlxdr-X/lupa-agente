"""Tool `buscar_web`: búsqueda en internet con la API de Tavily.

Tavily está pensada para agentes: devuelve título, URL y un extracto limpio de
cada resultado. La capa gratuita da 1.000 créditos al mes (1 por búsqueda básica).
"""

from __future__ import annotations

import requests

from ..llm.base import DefinicionTool
from .base import Contexto, ErrorTool, Fuente, Tool, entero

URL_TAVILY = "https://api.tavily.com/search"

DEF_BUSCAR_WEB = DefinicionTool(
    nombre="buscar_web",
    descripcion=(
        "Busca en internet contexto, explicaciones o noticias. Devuelve título, URL, fecha (si la hay) y un "
        "extracto de cada resultado. Úsala para explicar causas o contexto, NUNCA para sacar cifras que "
        "estén en datos.gov.co. Cita las URL que uses."
    ),
    parametros={
        "type": "object",
        "properties": {
            "consulta": {"type": "string", "description": "Qué buscar, en español y con año si aplica."},
            "noticias": {"type": "boolean", "description": "true para buscar solo noticias recientes."},
            "max_resultados": {"type": "integer", "description": "1 a 8. Por defecto 5."},
        },
        "required": ["consulta"],
    },
)


def buscar_web(
    api_key: str | None,
    contexto: Contexto,
    consulta: str,
    noticias: bool = False,
    max_resultados: int = 5,
    sesion: requests.Session | None = None,
) -> str:
    if not api_key:
        raise ErrorTool("buscar_web no está disponible porque falta TAVILY_API_KEY. Responde sin contexto web.")

    cuerpo = {
        "query": consulta,
        "max_results": entero(max_resultados, 5, 1, 8),
        "search_depth": "basic",
        "topic": "news" if noticias else "general",
    }
    try:
        r = (sesion or requests).post(
            URL_TAVILY, json=cuerpo, headers={"Authorization": f"Bearer {api_key}"}, timeout=30
        )
    except requests.RequestException as exc:
        raise ErrorTool(f"No se pudo conectar con Tavily: {exc}") from exc
    if r.status_code == 401:
        raise ErrorTool("Tavily rechazó la clave (401). Revisa TAVILY_API_KEY.")
    if r.status_code == 432 or r.status_code == 429:
        raise ErrorTool("Se acabó la cuota de Tavily o hay demasiadas peticiones. Responde sin contexto web.")
    if r.status_code >= 400:
        raise ErrorTool(f"Tavily respondió HTTP {r.status_code}: {r.text[:300]}")

    resultados = r.json().get("results", [])
    if not resultados:
        return f"No hubo resultados para '{consulta}'. Prueba con otras palabras."

    lineas = [f"Resultados web para '{consulta}':"]
    for i, res in enumerate(resultados, 1):
        titulo = res.get("title") or res.get("url", "")
        url = res.get("url", "")
        fecha = f" · {res['published_date'][:10]}" if res.get("published_date") else ""
        extracto = " ".join((res.get("content") or "").split())[:500]
        lineas.append(f"\n{i}. {titulo}{fecha}\n   {url}\n   {extracto}")
        if url:
            contexto.agregar_fuente(Fuente(tipo="web", titulo=titulo, url=url))
    return "\n".join(lineas)


def tool_buscar_web(api_key: str | None, contexto: Contexto) -> Tool:
    def funcion(consulta: str, noticias: bool = False, max_resultados: int = 5) -> str:
        return buscar_web(api_key, contexto, consulta, noticias, max_resultados)

    return Tool(DEF_BUSCAR_WEB, funcion)
