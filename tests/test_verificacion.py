"""Prueba la ida y vuelta con tools del script de verificación, con un LLM falso."""

from lupa.llm.base import LlamadaTool, Mensaje, RespuestaLLM, Uso
from lupa.verificacion import _solo_digitos, prueba_tools

from .conftest import ProveedorGuionado


def test_solo_digitos_quita_separadores_de_miles():
    assert _solo_digitos("Es 7.006.652 pesos") == "Es 7006652 pesos"
    assert _solo_digitos("7,006,652") == "7006652"
    assert _solo_digitos("7 006 652") == "7006652"


def test_ida_y_vuelta_con_tool(capsys):
    pide = RespuestaLLM(
        mensaje=Mensaje(
            rol="asistente", llamadas=[LlamadaTool(id="c1", nombre="multiplicar", argumentos={"a": 1234, "b": 5678})]
        ),
        uso=Uso(10, 5),
    )
    final = RespuestaLLM(mensaje=Mensaje(rol="asistente", texto="El resultado es 7.006.652."), uso=Uso(20, 8))
    llm = ProveedorGuionado([pide, final])

    assert prueba_tools(llm) is True

    # En la segunda vuelta el LLM recibió: pregunta, su llamada y el resultado de la tool
    historial = llm.llamadas_recibidas[1]["mensajes"]
    assert [m.rol for m in historial] == ["usuario", "asistente", "tool"]
    assert historial[2].texto == "7006652"
    assert "[OK]" in capsys.readouterr().out


def test_falla_si_el_llm_no_usa_la_tool():
    responde_de_memoria = RespuestaLLM(mensaje=Mensaje(rol="asistente", texto="Es 7006652"), uso=Uso())
    assert prueba_tools(ProveedorGuionado([responde_de_memoria])) is False
