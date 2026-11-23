"""Pruebas del ciclo del agente de punta a punta con un LLM guionado y datos falsos."""

import pytest

from lupa.agent import Agente
from lupa.config import Config
from lupa.llm.base import LlamadaTool, Mensaje, RespuestaLLM, Uso
from lupa.tools.datos_gov import ClienteSODA

from .conftest import ProveedorGuionado

TRM_MENSUAL = [
    {"mes": "2025-01-01T00:00:00.000", "trm": "4292.27"},
    {"mes": "2025-02-01T00:00:00.000", "trm": "4133.60"},
]


class SODAFalso(ClienteSODA):
    def __init__(self):
        super().__init__(carpeta_cache=None)
        self.consultas = []

    def get_json(self, ruta, params):
        self.consultas.append((ruta, params))
        if ruta.startswith("/resource/abcd"):
            from lupa.tools.base import ErrorTool

            raise ErrorTool("datos.gov.co rechazó la consulta (HTTP 404): dataset not found")
        if ruta.startswith("/resource/"):
            return TRM_MENSUAL
        return {"results": [{"resource": {"name": "TRM"}}]}


def pide(*llamadas, texto=""):
    lista = [LlamadaTool(f"c{i}", nombre, args) for i, (nombre, args) in enumerate(llamadas)]
    return RespuestaLLM(mensaje=Mensaje(rol="asistente", texto=texto, llamadas=lista), uso=Uso(100, 20))


def responde(texto):
    return RespuestaLLM(mensaje=Mensaje(rol="asistente", texto=texto), uso=Uso(150, 60))


@pytest.fixture
def config(entorno_limpio, tmp_path):
    entorno_limpio.setenv("LUPA_CARPETA_SALIDAS", str(tmp_path / "salidas"))
    return Config.cargar()


def crear_agente(config, tmp_path, respuestas, **kwargs):
    llm = ProveedorGuionado(respuestas)
    agente = Agente(llm, config, carpeta_trabajo=tmp_path / "trabajo", cliente_soda=SODAFalso(), **kwargs)
    return agente, llm


def test_flujo_completo_con_skill_consulta_grafica_y_respuesta(config, tmp_path):
    codigo = "df = pd.read_csv('tabla_1.csv')\ndf.plot(x='mes', y='trm')\nplt.savefig('trm.png')\nprint(len(df))"
    agente, llm = crear_agente(
        config,
        tmp_path,
        [
            pide(("cargar_skill", {"nombre": "explorar_datos"}), texto="Primero reviso el procedimiento."),
            pide(("consultar_dataset", {"dataset_id": "32sa-8pi3", "select": "date_trunc_ym(vigenciadesde) AS mes, avg(valor) AS trm", "group": "mes"})),
            pide(("ejecutar_python", {"codigo": codigo})),
            responde("La TRM promedio de enero de 2025 fue 4.292,27 pesos."),
        ],
    )
    res = agente.responder("¿Cómo estuvo la TRM a inicios de 2025?")

    assert res.completo and res.error is None
    assert res.respuesta.startswith("La TRM promedio")
    assert res.tools_usadas == ["cargar_skill", "consultar_dataset", "ejecutar_python"]
    assert res.skills_cargados == ["explorar_datos"]
    assert [g.name for g in res.graficas] == ["trm.png"]
    assert res.fuentes[0].url.endswith("/d/32sa-8pi3")
    assert (res.pasos, res.llamadas_llm, res.tokens_entrada) == (4, 4, 450)
    assert [e.tipo for e in res.eventos][0] == "pensamiento"

    # El prompt de sistema anuncia los skills y la tool cargar_skill está disponible
    assert "explorar_datos" in llm.llamadas_recibidas[0]["sistema"]
    assert "cargar_skill" in [t.nombre for t in llm.llamadas_recibidas[0]["tools"]]

    # La memoria guarda solo la pregunta y la respuesta final
    assert [m.rol for m in agente.historial] == ["usuario", "asistente"]


def test_se_recupera_de_un_error_de_tool(config, tmp_path):
    agente, llm = crear_agente(
        config,
        tmp_path,
        [
            pide(("consultar_dataset", {"dataset_id": "abcd-1234"})),
            pide(("consultar_dataset", {"dataset_id": "32sa-8pi3"})),
            responde("Listo."),
        ],
    )
    res = agente.responder("pregunta")
    assert res.errores_tool == 1
    assert res.errores_recuperados == 1
    # El LLM vio el error como texto en la segunda vuelta
    assert "ERROR" in llm.llamadas_recibidas[1]["mensajes"][-1].texto


def test_al_llegar_al_maximo_de_pasos_pide_respuesta_sin_tools(config, tmp_path):
    bucle = [pide(("calculadora", {"expresion": "1+1"})) for _ in range(3)]
    agente, llm = crear_agente(config, tmp_path, [*bucle, responde("Respuesta parcial.")], max_pasos=3)
    res = agente.responder("pregunta")

    assert not res.completo
    assert res.respuesta == "Respuesta parcial."
    assert llm.llamadas_recibidas[-1]["tools"] == []
    assert any(e.tipo == "aviso" for e in res.eventos)


def test_insiste_una_vez_si_la_respuesta_viene_vacia(config, tmp_path):
    agente, llm = crear_agente(config, tmp_path, [responde(""), responde("Ahora sí.")])
    res = agente.responder("pregunta")
    assert res.respuesta == "Ahora sí."
    assert llm.llamadas_recibidas[1]["mensajes"][-1].texto.startswith("Escribe ahora")


def test_un_fallo_del_llm_no_rompe_el_agente(config, tmp_path):
    agente, _ = crear_agente(config, tmp_path, [])  # sin respuestas: el LLM falso falla
    res = agente.responder("pregunta")
    assert res.error and "No pude completar" in res.respuesta
    assert agente.historial == []


def test_sin_skills_no_hay_cargar_skill(config, tmp_path):
    agente, llm = crear_agente(config, tmp_path, [responde("ok")], usar_skills=False)
    agente.responder("pregunta")
    assert "cargar_skill" not in [t.nombre for t in llm.llamadas_recibidas[0]["tools"]]
    assert "Skills disponibles" not in llm.llamadas_recibidas[0]["sistema"]


def test_la_segunda_pregunta_recibe_la_memoria(config, tmp_path):
    agente, llm = crear_agente(config, tmp_path, [responde("Uno."), responde("Dos.")])
    agente.responder("primera")
    agente.responder("segunda")
    mensajes = llm.llamadas_recibidas[1]["mensajes"]
    assert [m.texto for m in mensajes] == ["primera", "Uno.", "segunda"]
