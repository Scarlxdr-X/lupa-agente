"""Prueba la lógica de la interfaz con un LLM guionado (sin abrir el navegador)."""

import pytest

gr = pytest.importorskip("gradio")

from lupa.config import Config  # noqa: E402
from lupa.llm.base import LlamadaTool, Mensaje, RespuestaLLM, Uso  # noqa: E402
from lupa.ui import app as ui  # noqa: E402

from .conftest import ProveedorGuionado  # noqa: E402


def guion():
    codigo = "plt.plot([1, 2], [3, 4])\nplt.title('prueba')\nplt.savefig('prueba.png')\nprint('ok')"
    pasos = [
        [LlamadaTool("1", "cargar_skill", {"nombre": "visualizacion"})],
        [LlamadaTool("2", "calculadora", {"expresion": "(3706.97 - 4409.15) * 1000"})],
        [LlamadaTool("3", "ejecutar_python", {"codigo": codigo})],
    ]
    respuestas = [RespuestaLLM(Mensaje(rol="asistente", llamadas=ll), Uso(10, 5)) for ll in pasos]
    respuestas.append(RespuestaLLM(Mensaje(rol="asistente", texto="Perdiste 702.180 pesos."), Uso(10, 5)))
    return ProveedorGuionado(respuestas)


def test_preguntar_muestra_traza_graficas_y_respuesta(entorno_limpio, tmp_path, monkeypatch):
    entorno_limpio.setenv("LUPA_CARPETA_SALIDAS", str(tmp_path / "salidas"))
    config = Config.cargar()
    monkeypatch.setattr(ui, "crear_proveedor", lambda config, nombre: guion())

    actualizaciones, estados_del_chat = [], []
    for salida in ui.preguntar("¿Cuánto perdí?", [], None, "gemini", True, config):
        actualizaciones.append(salida)
        estados_del_chat.append(str(salida[0][-1]["content"]))  # Gradio lo envía en cada yield
    chat, traza, graficas, metricas, estado, entrada = actualizaciones[-1]

    assert chat[-1] == {"role": "assistant", "content": "Perdiste 702.180 pesos."}
    assert "calculadora" in traza and "-702180" in traza
    assert graficas[0].endswith("prueba.png")
    assert "visualizacion" in metricas
    assert entrada == ""
    # Mientras trabaja, el chat muestra en qué paso va
    assert any("Trabajando" in contenido for contenido in estados_del_chat[:-1])


def test_error_al_crear_el_agente_se_muestra_en_el_chat(entorno_limpio):
    config = Config.cargar()  # sin claves
    chat, *_ = list(ui.preguntar("hola", [], None, "gemini", True, config))[-1]
    assert "No pude iniciar el agente" in chat[-1]["content"]


def test_la_app_se_construye(entorno_limpio):
    assert isinstance(ui.construir_app(Config.cargar()), gr.Blocks)
