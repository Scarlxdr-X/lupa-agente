"""Pruebas del proveedor compatible con OpenAI (Groq) con un cliente falso."""

import json
from types import SimpleNamespace

import pytest

from lupa.llm.base import ErrorConfiguracion, LlamadaTool, Mensaje
from lupa.llm.openai_compat import ProveedorOpenAICompat

from .conftest import TOOL_EJEMPLO


def respuesta_falsa(content=None, tool_calls=None, finish_reason="stop"):
    mensaje = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=mensaje, finish_reason=finish_reason)],
        usage=SimpleNamespace(prompt_tokens=40, completion_tokens=12),
    )


def llamada_falsa(id_, nombre, argumentos_json):
    return SimpleNamespace(id=id_, function=SimpleNamespace(name=nombre, arguments=argumentos_json))


class CompletionsFalsas:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.peticiones = []

    def create(self, **kwargs):
        self.peticiones.append(kwargs)
        return self.respuestas.pop(0)


def cliente_falso(*respuestas):
    return SimpleNamespace(chat=SimpleNamespace(completions=CompletionsFalsas(respuestas)))


def test_sin_clave_da_error_claro():
    with pytest.raises(ErrorConfiguracion, match="GROQ_API_KEY"):
        ProveedorOpenAICompat(api_key=None)


def test_lee_llamadas_y_tokens():
    cliente = cliente_falso(
        respuesta_falsa(tool_calls=[llamada_falsa("call_1", "buscar_datasets", '{"consulta": "SECOP"}')],
                        finish_reason="tool_calls")
    )
    llm = ProveedorOpenAICompat(api_key=None, cliente=cliente)
    r = llm.generar([Mensaje.usuario("contratos")], tools=[TOOL_EJEMPLO], sistema="Eres Lupa")

    assert r.llamadas == [LlamadaTool(id="call_1", nombre="buscar_datasets", argumentos={"consulta": "SECOP"})]
    assert (r.uso.tokens_entrada, r.uso.tokens_salida) == (40, 12)
    assert r.motivo_fin == "tool_calls"

    peticion = cliente.chat.completions.peticiones[0]
    assert peticion["messages"][0] == {"role": "system", "content": "Eres Lupa"}
    assert peticion["tools"][0]["function"]["name"] == "buscar_datasets"


def test_json_invalido_se_marca_en_vez_de_romper():
    cliente = cliente_falso(respuesta_falsa(tool_calls=[llamada_falsa("c", "calculadora", "{no es json")]))
    r = ProveedorOpenAICompat(api_key=None, cliente=cliente).generar([Mensaje.usuario("x")])
    assert "_error_argumentos" in r.llamadas[0].argumentos


def test_historial_completo_en_formato_openai():
    llamada = LlamadaTool(id="call_1", nombre="calculadora", argumentos={"expresion": "1234*5678"})
    mensajes = [
        Mensaje.usuario("¿1234 por 5678?"),
        Mensaje(rol="asistente", llamadas=[llamada]),
        Mensaje.resultado_tool(llamada, "7006652"),
        Mensaje(rol="asistente", texto="Es 7.006.652"),
    ]
    salida = ProveedorOpenAICompat.a_mensajes(mensajes, sistema=None)

    assert [m["role"] for m in salida] == ["user", "assistant", "tool", "assistant"]
    assert salida[1]["content"] is None
    assert json.loads(salida[1]["tool_calls"][0]["function"]["arguments"]) == {"expresion": "1234*5678"}
    assert salida[2] == {"role": "tool", "tool_call_id": "call_1", "content": "7006652"}
    assert "tool_calls" not in salida[3]
