"""Interfaz web de Lupa con Gradio.

    lupa-app                 # abre en http://127.0.0.1:7860
    lupa-app --share         # además crea un enlace público temporal (útil en Colab)

A la izquierda está el chat; a la derecha, las gráficas, la traza del agente
(cada tool que llamó, con qué argumentos y qué obtuvo) y las métricas.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterator

import gradio as gr

from ..agent import Agente, Evento, Resultado
from ..config import Config
from ..llm import crear_proveedor

EJEMPLOS = [
    "¿Cuánto contrató la Gobernación del Valle del Cauca por SECOP II en 2025, por dependencia? Muestra una gráfica y busca si hubo noticias sobre esa contratación.",
    "Grafica la TRM promedio mensual de 2025 y explica qué movió el dólar ese año.",
    "Si compré 1.000 dólares el 2 de enero de 2025 y los vendí el 30 de diciembre de 2025, ¿cuánto gané o perdí en pesos?",
    "Compara el puntaje global promedio de Saber 11 entre colegios oficiales y no oficiales del Valle del Cauca en 2019 y 2022.",
    "¿Qué datos abiertos hay sobre calidad del aire en Bogotá?",
]

MAX_RESULTADO_TRAZA = 700


# ---------------------------------------------------------------------------
# Formato de la traza y las métricas
# ---------------------------------------------------------------------------


def formatear_evento(evento: Evento) -> str:
    if evento.tipo == "pensamiento":
        return f"**Paso {evento.paso} · razonamiento:** {evento.texto}"
    if evento.tipo == "llamada":
        argumentos = json.dumps(evento.argumentos or {}, ensure_ascii=False)
        if len(argumentos) > 400:
            argumentos = argumentos[:400] + "…"
        return f"**Paso {evento.paso} · {evento.tool}**\n```json\n{argumentos}\n```"
    if evento.tipo == "resultado":
        marca = "resultado" if evento.ok else "ERROR"
        texto = evento.texto if len(evento.texto) <= MAX_RESULTADO_TRAZA else evento.texto[:MAX_RESULTADO_TRAZA] + "\n…"
        return f"{marca} ({evento.duracion_s:.1f} s):\n```text\n{texto}\n```"
    if evento.tipo in ("aviso", "error"):
        return f"**{evento.tipo.upper()}:** {evento.texto}"
    return ""


def formatear_metricas(res: Resultado) -> str:
    skills = ", ".join(res.skills_cargados) or "ninguno"
    fuentes = "\n".join(f"- [{f.titulo}]({f.url})" for f in res.fuentes) or "- (ninguna)"
    return (
        f"**Pasos:** {res.pasos} · **Llamadas al LLM:** {res.llamadas_llm} · "
        f"**Tools:** {len(res.tools_usadas)} ({res.errores_tool} con error, {res.errores_recuperados} recuperados) · "
        f"**Tokens:** {res.tokens_entrada + res.tokens_salida:,} · **Tiempo:** {res.duracion_s:.1f} s\n\n"
        f"**Skills cargados:** {skills}\n\n**Fuentes consultadas:**\n{fuentes}"
    )


def estado_trabajando(evento: Evento) -> str:
    if evento.tipo == "llamada":
        return f"_Trabajando… paso {evento.paso}: {evento.tool}_"
    return f"_Trabajando… paso {evento.paso}_"


# ---------------------------------------------------------------------------
# Lógica de la interfaz
# ---------------------------------------------------------------------------


def obtener_agente(estado: dict | None, proveedor: str, usar_skills: bool, config: Config) -> dict:
    """Crea un agente nuevo si no hay uno o si cambió el LLM o la opción de skills."""
    if estado and estado["proveedor"] == proveedor and estado["usar_skills"] == usar_skills:
        return estado
    agente = Agente(crear_proveedor(config, proveedor), config, usar_skills=usar_skills)
    return {"agente": agente, "proveedor": proveedor, "usar_skills": usar_skills}


def preguntar(
    pregunta: str, chat: list[dict], estado: dict | None, proveedor: str, usar_skills: bool, config: Config
) -> Iterator[tuple[Any, ...]]:
    chat = list(chat or [])
    pregunta = (pregunta or "").strip()
    if not pregunta:
        yield chat, gr.update(), gr.update(), gr.update(), estado, ""
        return

    chat += [{"role": "user", "content": pregunta}, {"role": "assistant", "content": "_Pensando…_"}]
    try:
        estado = obtener_agente(estado, proveedor, usar_skills, config)
    except Exception as exc:  # noqa: BLE001 - p. ej. falta la clave del proveedor elegido
        chat[-1]["content"] = f"No pude iniciar el agente: {exc}"
        yield chat, "", [], "", estado, ""
        return

    agente: Agente = estado["agente"]
    traza: list[str] = []
    yield chat, "", [], "", estado, ""

    for evento in agente.responder_por_pasos(pregunta):
        if evento.tipo == "respuesta":
            break
        bloque = formatear_evento(evento)
        if bloque:
            traza.append(bloque)
        chat[-1]["content"] = estado_trabajando(evento)
        yield chat, "\n\n".join(traza), gr.update(), gr.update(), estado, ""

    res = agente.ultimo_resultado
    chat[-1]["content"] = res.respuesta
    graficas = [str(p) for p in res.graficas]
    yield chat, "\n\n".join(traza), graficas, formatear_metricas(res), estado, ""


def nueva_conversacion(estado: dict | None):
    if estado:
        estado["agente"].reiniciar()
    return [], "", [], "", estado


def construir_app(config: Config | None = None) -> gr.Blocks:
    config = config or Config.cargar()

    with gr.Blocks(title="Lupa · datos abiertos de Colombia", fill_width=True) as app:
        gr.Markdown(
            "# Lupa\nPregunta en español sobre los datos abiertos de Colombia (datos.gov.co). "
            "El agente busca el conjunto, lo consulta, lo analiza, grafica y cita sus fuentes."
        )
        estado = gr.State(None)
        with gr.Row():
            with gr.Column(scale=3):
                chat = gr.Chatbot(label="Conversación", height=560, latex_delimiters=[])
                entrada = gr.Textbox(label="Tu pregunta", placeholder="Ej.: ¿Cuál fue la TRM promedio de octubre de 2025?")
                with gr.Row():
                    enviar = gr.Button("Preguntar", variant="primary")
                    limpiar = gr.Button("Nueva conversación")
                gr.Examples(examples=[[e] for e in EJEMPLOS], inputs=[entrada], label="Preguntas de ejemplo")
            with gr.Column(scale=2):
                with gr.Row():
                    proveedor = gr.Dropdown(
                        choices=[("Gemini", "gemini"), ("Groq (respaldo)", "openai_compat")],
                        value=config.proveedor,
                        label="Modelo de lenguaje",
                    )
                    usar_skills = gr.Checkbox(value=True, label="Usar skills")
                galeria = gr.Gallery(label="Gráficas", columns=1, height=320)
                metricas = gr.Markdown()
                with gr.Accordion("Traza del agente", open=True):
                    traza = gr.Markdown()

        def _preguntar(p, c, e, prov, skills):
            yield from preguntar(p, c, e, prov, skills, config)

        salidas = [chat, traza, galeria, metricas, estado, entrada]
        entradas = [entrada, chat, estado, proveedor, usar_skills]
        enviar.click(_preguntar, entradas, salidas)
        entrada.submit(_preguntar, entradas, salidas)
        limpiar.click(nueva_conversacion, [estado], [chat, traza, galeria, metricas, estado])

    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Interfaz web de Lupa.")
    parser.add_argument("--share", action="store_true", help="Crea un enlace público temporal (Colab).")
    parser.add_argument("--puerto", type=int, default=7860)
    args = parser.parse_args(argv)

    config = Config.cargar()
    salidas = Path(config.carpeta_salidas).resolve()
    salidas.mkdir(parents=True, exist_ok=True)
    construir_app(config).queue().launch(share=args.share, server_port=args.puerto, allowed_paths=[str(salidas)])


if __name__ == "__main__":
    main()
