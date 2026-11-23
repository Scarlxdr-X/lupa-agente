import json
from pathlib import Path

import pytest

from lupa import evaluacion as ev
from lupa.agent.agente import Evento, Resultado
from lupa.tools.datos_gov import ClienteSODA


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("La TRM fue $4.409,15 pesos", 4409.15),
        ("TRM: 4,409.15", 4409.15),
        ("perdiste 702.180 pesos", 702180),
        ("fue de 3881.44", 3881.44),
        ("unos 483 mil millones de pesos", 483e9),
        ("1,2 billones", 1.2e12),
        ("se firmaron 893 contratos", 893),
    ],
)
def test_extrae_numeros_en_varios_formatos(texto, esperado):
    assert any(abs(n - esperado) / esperado < 1e-9 for n in ev.extraer_numeros(texto))


def test_contiene_numero_con_tolerancia_y_valor_absoluto():
    assert ev.contiene_numero("Perdiste 702.180 pesos.", -702180, 0.005, absoluto=True)
    assert not ev.contiene_numero("Perdiste 702.180 pesos.", -702180, 0.005, absoluto=False)
    assert ev.contiene_numero("Promedio 241,9 puntos", 241.87, 0.01)
    assert not ev.contiene_numero("Promedio 230 puntos", 241.87, 0.01)


class SODAFijo(ClienteSODA):
    def __init__(self, valores):
        super().__init__(carpeta_cache=None)
        self.valores = list(valores)

    def get_json(self, ruta, params):
        return [{"v": str(self.valores.pop(0))}]


def resultado(respuesta, eventos=(), graficas=()):
    return Resultado(pregunta="p", respuesta=respuesta, eventos=list(eventos), graficas=[Path(g) for g in graficas])


def test_verificar_numero_con_expresion():
    verif = [{"tipo": "numero", "consultas": {"a": {"dataset": "x", "select": "v"}, "b": {"dataset": "x", "select": "v"}},
              "expresion": "1000 * (b - a)", "absoluto": True, "tolerancia": 0.005}]
    chequeos = ev.verificar(resultado("Perdiste 702.180 pesos"), verif, SODAFijo([4409.15, 3706.97]))
    assert chequeos[0].ok


def test_verificar_grafica_web_dataset_y_tools():
    eventos = [
        Evento("llamada", 1, tool="consultar_dataset", argumentos={"dataset_id": "32sa-8pi3"}),
        Evento("resultado", 1, "ok", tool="consultar_dataset", ok=True),
        Evento("llamada", 2, tool="buscar_web", argumentos={"consulta": "dólar"}),
        Evento("resultado", 2, "ERROR", tool="buscar_web", ok=False),
    ]
    res = resultado("Ver https://ejemplo.co", eventos, ["g.png"])
    verif = [{"tipo": "dataset", "id": "32sa-8pi3"}, {"tipo": "grafica"}, {"tipo": "web"},
             {"tipo": "tools_exitosas", "tools": ["consultar_dataset", "buscar_web"]}]
    assert [c.ok for c in ev.verificar(res, verif, SODAFijo([]))] == [True, True, True, False]


def test_precision_de_tools():
    eventos = [Evento("llamada", 1, tool=t) for t in ("cargar_skill", "consultar_dataset", "buscar_web")]
    assert ev.precision_tools(resultado("", eventos), ["consultar_dataset"]) == pytest.approx(2 / 3)


def test_el_banco_de_tareas_es_valido():
    tareas = json.loads(ev.ARCHIVO_TAREAS.read_text(encoding="utf-8"))["tareas"]
    assert len(tareas) == 12
    assert {t["nivel"] for t in tareas} == set(ev.NIVELES)
    assert len({t["id"] for t in tareas}) == 12
    for t in tareas:
        assert t["verificaciones"] and t["tools_esperadas"]


def test_resumen_tabla_y_grafica(tmp_path):
    def reg(config, nivel, exito):
        return ev.RegistroTarea("T", nivel, config, exito, [], 1.0, 3, 3, ["consultar_dataset"], [], 1, 1, 900, 12.0, True, None)

    registros = [reg("sin_skills", "simple", True), reg("sin_skills", "compleja", False),
                 reg("con_skills", "simple", True), reg("con_skills", "compleja", True)]
    resumen = ev.resumir(registros)
    assert resumen["sin_skills"]["exito_total"] == 0.5
    assert resumen["con_skills"]["exito_compleja"] == 1.0

    ev.escribir_resumen_md(resumen, registros, tmp_path / "resumen.md", "gemini")
    texto = (tmp_path / "resumen.md").read_text(encoding="utf-8")
    assert "| Tasa de éxito (total) | 50 % | 100 % |" in texto

    ev.graficar(resumen, tmp_path / "exito.png")
    assert (tmp_path / "exito.png").stat().st_size > 10_000


def test_unir_corridas_parciales(tmp_path):
    def reg(tarea, config, exito):
        return ev.RegistroTarea(tarea, "simple", config, exito, [], 1.0, 3, 3, ["consultar_dataset"], [], 0, 0, 900, 12.0, True, None)

    from dataclasses import asdict
    import json

    parte1, parte2 = tmp_path / "p1", tmp_path / "p2"
    parte1.mkdir()
    parte2.mkdir()
    (parte1 / "resultados.json").write_text(json.dumps([asdict(reg("S1", "con_skills", False))]), encoding="utf-8")
    # La corrida más reciente de la misma tarea reemplaza a la anterior
    (parte2 / "resultados.json").write_text(
        json.dumps([asdict(reg("S1", "con_skills", True)), asdict(reg("S2", "con_skills", True))]), encoding="utf-8"
    )
    resumen = ev.unir_resultados([parte1, parte2], tmp_path / "combinado", "gemini")
    assert resumen["con_skills"]["tareas"] == 2
    assert resumen["con_skills"]["exito_total"] == 1.0
    assert (tmp_path / "combinado" / "exito_por_nivel.png").exists()
