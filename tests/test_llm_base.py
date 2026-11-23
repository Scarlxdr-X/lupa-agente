import pytest

from lupa.llm.base import LlamadaTool, Mensaje, RespuestaLLM, Uso, con_reintentos

from .conftest import ProveedorGuionado


class ErrorTemporal(Exception):
    pass


def test_reintenta_errores_temporales_y_luego_funciona():
    intentos = {"n": 0}
    esperas = []

    def funcion():
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise ErrorTemporal("429")
        return "ok"

    resultado = con_reintentos(
        funcion, lambda e: isinstance(e, ErrorTemporal), max_reintentos=4, espera_inicial=1, dormir=esperas.append
    )
    assert resultado == "ok"
    assert intentos["n"] == 3
    assert len(esperas) == 2
    assert esperas[1] > esperas[0]  # la espera crece


def test_no_reintenta_errores_permanentes():
    esperas = []

    def funcion():
        raise ValueError("clave inválida")

    with pytest.raises(ValueError):
        con_reintentos(funcion, lambda e: isinstance(e, ErrorTemporal), dormir=esperas.append)
    assert esperas == []


def test_se_rinde_al_agotar_reintentos():
    def funcion():
        raise ErrorTemporal("429")

    with pytest.raises(ErrorTemporal):
        con_reintentos(funcion, lambda e: True, max_reintentos=2, dormir=lambda s: None)


def test_generar_marca_proveedor_y_duracion():
    respuesta = RespuestaLLM(mensaje=Mensaje(rol="asistente", texto="hola"), uso=Uso())
    llm = ProveedorGuionado([respuesta])
    salida = llm.generar([Mensaje.usuario("hola")])
    assert salida.mensaje.proveedor == "guionado"
    assert salida.duracion_s >= 0
    assert not salida.pide_tools


def test_resultado_tool_enlaza_con_su_llamada():
    llamada = LlamadaTool(id="c1", nombre="calculadora", argumentos={"expresion": "2+2"})
    m = Mensaje.resultado_tool(llamada, "4")
    assert (m.rol, m.id_llamada, m.nombre_tool, m.texto) == ("tool", "c1", "calculadora", "4")
