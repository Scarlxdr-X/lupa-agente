"""Pruebas del proveedor Gemini con un cliente falso (sin red)."""

from types import SimpleNamespace

import pytest
from google.genai import errors, types

from lupa.llm.base import ErrorConfiguracion, LlamadaTool, Mensaje
from lupa.llm.gemini import ProveedorGemini

from .conftest import TOOL_EJEMPLO


class ModelosFalsos:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.peticiones = []

    def generate_content(self, model, contents, config):
        self.peticiones.append({"model": model, "contents": contents, "config": config})
        return self.respuestas.pop(0)


def cliente_falso(*respuestas):
    return SimpleNamespace(models=ModelosFalsos(respuestas))


def respuesta_con_llamada(nombre, args, id_llamada=None, firma=b"firma-secreta"):
    content = types.Content(
        role="model",
        parts=[
            types.Part(
                function_call=types.FunctionCall(id=id_llamada, name=nombre, args=args),
                thought_signature=firma,
            )
        ],
    )
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=content, finish_reason="STOP")],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=100, candidates_token_count=20, thoughts_token_count=30
        ),
    )


def respuesta_texto(texto):
    content = types.Content(
        role="model",
        parts=[types.Part(text="pensando...", thought=True), types.Part(text=texto)],
    )
    return types.GenerateContentResponse(candidates=[types.Candidate(content=content, finish_reason="STOP")])


def test_sin_clave_da_error_claro():
    with pytest.raises(ErrorConfiguracion, match="GEMINI_API_KEY"):
        ProveedorGemini(api_key=None)


def test_lee_llamada_a_tool_y_tokens():
    cliente = cliente_falso(respuesta_con_llamada("buscar_datasets", {"consulta": "TRM"}))
    llm = ProveedorGemini(api_key=None, cliente=cliente)
    r = llm.generar([Mensaje.usuario("¿Cuál fue la TRM?")], tools=[TOOL_EJEMPLO])

    assert r.pide_tools
    assert r.llamadas[0].nombre == "buscar_datasets"
    assert r.llamadas[0].argumentos == {"consulta": "TRM"}
    assert r.llamadas[0].id.startswith("lupa-")  # Gemini no envió id
    assert r.uso.tokens_entrada == 100
    assert r.uso.tokens_salida == 50  # salida + pensamiento
    assert r.motivo_fin == "STOP"


def test_texto_excluye_pensamientos():
    llm = ProveedorGemini(api_key=None, cliente=cliente_falso(respuesta_texto("La TRM fue 3.800")))
    r = llm.generar([Mensaje.usuario("hola")])
    assert r.texto == "La TRM fue 3.800"


def test_config_desactiva_function_calling_automatico():
    cliente = cliente_falso(respuesta_texto("ok"))
    llm = ProveedorGemini(api_key=None, modelo="gemini-prueba", cliente=cliente)
    llm.generar([Mensaje.usuario("hola")], tools=[TOOL_EJEMPLO], sistema="Eres Lupa")

    peticion = cliente.models.peticiones[0]
    assert peticion["model"] == "gemini-prueba"
    assert peticion["config"].automatic_function_calling.disable is True
    assert peticion["config"].system_instruction == "Eres Lupa"
    declaracion = peticion["config"].tools[0].function_declarations[0]
    assert declaracion.name == "buscar_datasets"
    assert declaracion.parameters_json_schema["required"] == ["consulta"]


def test_reenvia_el_content_original_con_su_firma():
    """Gemini 3 exige recibir de vuelta la firma de pensamiento (si no: error 400)."""
    cliente = cliente_falso(respuesta_con_llamada("buscar_datasets", {"consulta": "TRM"}), respuesta_texto("listo"))
    llm = ProveedorGemini(api_key=None, cliente=cliente)

    mensajes = [Mensaje.usuario("¿TRM?")]
    r1 = llm.generar(mensajes, tools=[TOOL_EJEMPLO])
    mensajes += [r1.mensaje, Mensaje.resultado_tool(r1.llamadas[0], "32sa-8pi3")]
    llm.generar(mensajes, tools=[TOOL_EJEMPLO])

    contents = cliente.models.peticiones[1]["contents"]
    assert [c.role for c in contents] == ["user", "model", "user"]
    assert contents[1].parts[0].thought_signature == b"firma-secreta"
    respuesta_tool = contents[2].parts[0].function_response
    assert respuesta_tool.name == "buscar_datasets"
    assert respuesta_tool.response == {"resultado": "32sa-8pi3"}
    assert respuesta_tool.id is None  # el id `lupa-...` no se envía


def test_resultados_paralelos_van_en_un_solo_content():
    llm = ProveedorGemini(api_key=None, cliente=cliente_falso())
    a = LlamadaTool(id="a1", nombre="buscar_web", argumentos={})
    b = LlamadaTool(id="b2", nombre="calculadora", argumentos={})
    mensajes = [
        Mensaje.usuario("pregunta"),
        Mensaje(rol="asistente", llamadas=[a, b]),
        Mensaje.resultado_tool(a, "r1"),
        Mensaje.resultado_tool(b, "r2"),
        Mensaje.usuario("otra pregunta"),
    ]
    contents = llm.a_contents(mensajes)

    assert [c.role for c in contents] == ["user", "model", "user", "user"]
    assert len(contents[2].parts) == 2
    assert [p.function_response.id for p in contents[2].parts] == ["a1", "b2"]


def test_reconstruye_mensajes_de_otro_proveedor():
    llm = ProveedorGemini(api_key=None, cliente=cliente_falso())
    mensaje = Mensaje(
        rol="asistente",
        texto="Voy a buscar",
        llamadas=[LlamadaTool(id="call_9", nombre="buscar_web", argumentos={"q": "dólar"})],
        proveedor="openai_compat",
    )
    content = llm.a_contents([mensaje])[0]
    assert content.role == "model"
    assert content.parts[0].text == "Voy a buscar"
    assert content.parts[1].function_call.name == "buscar_web"
    assert content.parts[1].function_call.id == "call_9"


def test_clasifica_errores_reintentables():
    error_429 = errors.ClientError(429, {"error": {"code": 429, "message": "cuota", "status": "RESOURCE_EXHAUSTED"}})
    error_400 = errors.ClientError(400, {"error": {"code": 400, "message": "mal", "status": "INVALID_ARGUMENT"}})
    llm = ProveedorGemini(api_key=None, cliente=cliente_falso())
    assert llm._es_reintentable(error_429)
    assert not llm._es_reintentable(error_400)
    assert not llm._es_reintentable(ValueError("otra cosa"))


# --- Modelos de respaldo -----------------------------------------------------


class ModelosSaturados(ModelosFalsos):
    """Responde 503 para los modelos de `saturados` y entrega respuestas para el resto."""

    def __init__(self, respuestas, saturados):
        super().__init__(respuestas)
        self.saturados = set(saturados)

    def generate_content(self, model, contents, config):
        self.peticiones.append({"model": model, "contents": contents, "config": config})
        if model in self.saturados:
            raise errors.ServerError(503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}})
        return self.respuestas.pop(0)


def test_si_el_modelo_esta_saturado_usa_el_de_respaldo():
    modelos = ModelosSaturados([respuesta_texto("listo")], saturados={"principal"})
    llm = ProveedorGemini(None, modelo="principal", modelos_respaldo=["respaldo"],
                          cliente=SimpleNamespace(models=modelos), max_reintentos=0)
    r = llm.generar([Mensaje.usuario("hola")])
    assert r.texto == "listo"
    assert [p["model"] for p in modelos.peticiones] == ["principal", "respaldo"]
    assert llm.modelo == "respaldo" and r.mensaje.modelo == "respaldo"


def test_si_todos_estan_saturados_se_propaga_el_error():
    modelos = ModelosSaturados([], saturados={"a", "b"})
    llm = ProveedorGemini(None, modelo="a", modelos_respaldo=["b", "a"],
                          cliente=SimpleNamespace(models=modelos), max_reintentos=0)
    with pytest.raises(errors.ServerError):
        llm.generar([Mensaje.usuario("hola")])
    assert [p["model"] for p in modelos.peticiones] == ["a", "b"]  # sin repetir modelos


def test_al_cambiar_de_modelo_las_firmas_viejas_se_reemplazan():
    llm = ProveedorGemini(None, modelo="nuevo", cliente=cliente_falso())
    viejo = ProveedorGemini(None, modelo="viejo", cliente=cliente_falso())
    r1 = viejo.desde_respuesta(respuesta_con_llamada("calculadora", {"expresion": "1+1"}))
    llamada = r1.llamadas[0]
    historial = [Mensaje.usuario("¿1+1?"), r1.mensaje, Mensaje.resultado_tool(llamada, "2")]

    # Para el mismo modelo, se reenvía tal cual
    assert viejo.a_contents(historial)[1] is r1.mensaje.nativo
    # Para otro modelo, la firma original se cambia por la comodín
    parte = llm.a_contents(historial)[1].parts[0]
    assert parte.function_call.name == "calculadora"
    assert parte.thought_signature == b"skip_thought_signature_validator"


def test_config_lee_los_modelos_de_respaldo(monkeypatch):
    from lupa.config import Config

    monkeypatch.setenv("LUPA_MODELOS_RESPALDO_GEMINI", "m1, m2,,m3")
    assert Config.cargar().modelos_respaldo_gemini == ("m1", "m2", "m3")
