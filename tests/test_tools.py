"""Pruebas de las tools, sin red: las APIs se reemplazan por respuestas preparadas."""

from types import SimpleNamespace

import pandas as pd
import pytest

from lupa.llm.base import DefinicionTool, LlamadaTool
from lupa.tools.base import Contexto, ErrorTool, RegistroTools, Tool
from lupa.tools.calculadora import calculadora, evaluar
from lupa.tools.datos_gov import (
    ClienteSODA,
    buscar_datasets,
    columnas_personales_en,
    consultar_dataset,
    es_columna_personal,
)
from lupa.tools.python_exec import ejecutar_python
from lupa.tools.web import buscar_web

# ---------------------------------------------------------------------------
# Dobles de prueba
# ---------------------------------------------------------------------------

CATALOGO_TRM = {
    "resultSetSize": 1,
    "results": [
        {
            "resource": {
                "name": "Tasa de Cambio Representativa del Mercado- TRM",
                "id": "32sa-8pi3",
                "description": "La TRM corresponde al promedio ponderado...",
                "attribution": "Superintendencia Financiera de Colombia",
                "data_updated_at": "2026-11-19T23:05:21.000Z",
                "columns_field_name": ["valor", "vigenciadesde", "vigenciahasta", "unidad"],
                "columns_datatype": ["Number", "Calendar date", "Calendar date", "Text"],
                "columns_description": ["Valor numérico", "Inicio", "Fin", "ISO 4217"],
            }
        }
    ],
}


class RespuestaHTTP:
    def __init__(self, datos, status=200):
        self._datos, self.status_code, self.text = datos, status, str(datos)

    def json(self):
        return self._datos


class SesionFalsa:
    """Imita requests.Session: devuelve la respuesta según la ruta pedida."""

    def __init__(self, respuestas):
        self.respuestas = respuestas  # {fragmento_de_url: RespuestaHTTP}
        self.peticiones = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.peticiones.append({"url": url, "params": params})
        for fragmento, respuesta in self.respuestas.items():
            if fragmento in url:
                return respuesta
        raise AssertionError(f"URL no esperada: {url}")


def cliente(respuestas, tmp_path=None, horas_cache=0):
    sesion = SesionFalsa(respuestas)
    carpeta = (tmp_path / "cache") if tmp_path else None
    return ClienteSODA(carpeta_cache=carpeta, horas_cache=horas_cache, sesion=sesion), sesion


@pytest.fixture
def contexto(tmp_path):
    return Contexto(tmp_path / "trabajo")


# ---------------------------------------------------------------------------
# calculadora
# ---------------------------------------------------------------------------


def test_calculadora_exacta_y_formato_colombiano():
    assert evaluar("(3706.97 - 4409.15) * 1000") == pytest.approx(-702180)
    texto = calculadora("1234 * 5678")
    assert "7006652" in texto and "7.006.652" in texto


def test_calculadora_funciones_y_variables():
    assert evaluar("round(sqrt(16) + max(1, 2), 1)") == 6
    assert evaluar("a / b * 100", {"a": 1, "b": 4}) == 25


@pytest.mark.parametrize("expresion", ["__import__('os')", "open('x')", "2 ** 99999", "1 / 0", "1,000"])
def test_calculadora_rechaza_lo_peligroso_o_invalido(expresion):
    with pytest.raises(ErrorTool):
        evaluar(expresion)


# ---------------------------------------------------------------------------
# datos.gov.co
# ---------------------------------------------------------------------------


def test_detecta_columnas_personales():
    assert es_columna_personal("documento_proveedor")
    assert es_columna_personal("n_mero_de_cuenta")
    assert es_columna_personal("nombre_supervisor")
    assert es_columna_personal("estu_fechanacimiento")
    assert not es_columna_personal("valor_del_contrato")
    assert not es_columna_personal("documentos_tipo")


def test_texto_entre_comillas_no_cuenta_como_columna():
    assert columnas_personales_en("upper(nombre_entidad) like '%CUENTA%'") == []
    assert columnas_personales_en("documento_proveedor = '123'") == ["documento_proveedor"]


def test_buscar_datasets_lista_columnas():
    cli, sesion = cliente({"/api/catalog/v1": RespuestaHTTP(CATALOGO_TRM)})
    texto = buscar_datasets(cli, "tasa de cambio")
    assert "32sa-8pi3" in texto
    assert "valor (Number" in texto
    assert sesion.peticiones[0]["params"]["q"] == "tasa de cambio"


def test_buscar_datasets_por_id():
    cli, sesion = cliente({"/api/catalog/v1": RespuestaHTTP(CATALOGO_TRM)})
    buscar_datasets(cli, "32SA-8PI3")
    assert sesion.peticiones[0]["params"]["ids"] == "32sa-8pi3"


def test_consultar_guarda_csv_convierte_numeros_y_quita_personales(contexto):
    filas = [
        {"nombre_entidad": "GOBERNACION", "valor_del_contrato": "1000", "documento_proveedor": "123", "codigo_entidad": "0701"},
        {"nombre_entidad": "ALCALDIA", "valor_del_contrato": "2500.5", "documento_proveedor": "456", "codigo_entidad": "0702"},
    ]
    cli, _ = cliente({"/resource/": RespuestaHTTP(filas), "/api/catalog/v1": RespuestaHTTP(CATALOGO_TRM)})
    texto = consultar_dataset(cli, contexto, "jbjy-vk9h", limit=10)

    tabla = pd.read_csv(contexto.carpeta / "tabla_1.csv", dtype={"codigo_entidad": str})
    assert list(tabla.columns) == ["nombre_entidad", "valor_del_contrato", "codigo_entidad"]
    assert tabla["valor_del_contrato"].sum() == pytest.approx(3500.5)
    assert tabla["codigo_entidad"].tolist() == ["0701", "0702"]  # los códigos conservan los ceros
    assert "Se omitieron 1 columnas" in texto
    assert contexto.fuentes[0].url == "https://www.datos.gov.co/d/jbjy-vk9h"


def test_consultar_bloquea_filtros_con_datos_personales(contexto):
    cli, sesion = cliente({})
    with pytest.raises(ErrorTool, match="datos personales"):
        consultar_dataset(cli, contexto, "jbjy-vk9h", where="documento_proveedor = '123'")
    assert sesion.peticiones == []


def test_consultar_valida_id(contexto):
    cli, _ = cliente({})
    with pytest.raises(ErrorTool, match="formato"):
        consultar_dataset(cli, contexto, "TRM")


def test_consultar_avisa_limite_y_resultado_vacio(contexto):
    cli, _ = cliente({"/resource/": RespuestaHTTP([{"a": "1"}, {"a": "2"}]), "/api/catalog/v1": RespuestaHTTP({})})
    assert "AVISO: se alcanzó el límite de 2 filas" in consultar_dataset(cli, contexto, "abcd-1234", limit=2)

    cli, _ = cliente({"/resource/": RespuestaHTTP([]), "/api/catalog/v1": RespuestaHTTP({})})
    assert "no devolvió filas" in consultar_dataset(cli, contexto, "abcd-1234")


def test_error_de_la_api_llega_como_mensaje_util(contexto):
    error = RespuestaHTTP({"message": "Could not parse SoQL query"}, status=400)
    cli, _ = cliente({"/resource/": error})
    with pytest.raises(ErrorTool, match="Could not parse SoQL"):
        consultar_dataset(cli, contexto, "abcd-1234", where="mal escrito")


def test_cache_evita_repetir_peticiones(tmp_path):
    cli, sesion = cliente({"/api/catalog/v1": RespuestaHTTP(CATALOGO_TRM)}, tmp_path, horas_cache=1)
    buscar_datasets(cli, "trm")
    buscar_datasets(cli, "trm")
    assert len(sesion.peticiones) == 1


# ---------------------------------------------------------------------------
# ejecutar_python
# ---------------------------------------------------------------------------


def test_ejecuta_codigo_con_las_tablas_y_registra_graficas(contexto):
    pd.DataFrame({"mes": ["2025-01", "2025-02"], "trm": [4292.27, 4133.6]}).to_csv(
        contexto.carpeta / "tabla_1.csv", index=False
    )
    codigo = (
        "df = pd.read_csv('tabla_1.csv')\n"
        "print(round(df['trm'].mean(), 2))\n"
        "df.plot(x='mes', y='trm')\n"
        "plt.savefig('trm.png')\n"
    )
    texto = ejecutar_python(contexto, codigo)
    assert "4212.94" in texto or "4,212.94" in texto
    assert "trm.png" in texto
    assert contexto.graficas == [contexto.carpeta / "trm.png"]


def test_error_de_python_vuelve_con_la_linea_correcta(contexto):
    with pytest.raises(ErrorTool) as info:
        ejecutar_python(contexto, "x = 1\ny = x + noexiste\n")
    assert "NameError" in str(info.value)
    assert "line 2" in str(info.value)


def test_rechaza_operaciones_peligrosas(contexto):
    with pytest.raises(ErrorTool, match="no está permitido"):
        ejecutar_python(contexto, "import subprocess\nsubprocess.run(['ls'])")


def test_tiempo_limite(contexto):
    with pytest.raises(ErrorTool, match="tardó más"):
        ejecutar_python(contexto, "import time\ntime.sleep(5)", timeout_s=1)


# ---------------------------------------------------------------------------
# buscar_web
# ---------------------------------------------------------------------------


def test_buscar_web_sin_clave(contexto):
    with pytest.raises(ErrorTool, match="TAVILY_API_KEY"):
        buscar_web(None, contexto, "dólar 2025")


def test_buscar_web_formatea_y_registra_fuentes(contexto):
    datos = {"results": [{"title": "El dólar cae", "url": "https://ejemplo.co/a", "content": "Texto", "published_date": "2025-11-01T10:00:00"}]}
    sesion = SimpleNamespace(post=lambda *a, **k: RespuestaHTTP(datos))
    texto = buscar_web("clave", contexto, "dólar Colombia 2025", sesion=sesion)
    assert "El dólar cae · 2025-11-01" in texto
    assert contexto.fuentes[0].tipo == "web"


# ---------------------------------------------------------------------------
# RegistroTools
# ---------------------------------------------------------------------------


def _registro():
    definicion = DefinicionTool("sumar", "Suma", {"type": "object", "properties": {}, "required": ["a", "b"]})

    def sumar(a, b):
        if a == "falla":
            raise ValueError("explotó")
        return str(a + b)

    return RegistroTools([Tool(definicion, sumar)])


def test_registro_ejecuta_e_ignora_argumentos_inventados():
    r = _registro().ejecutar(LlamadaTool("1", "sumar", {"a": 2, "b": 3, "inventado": True}))
    assert (r.texto, r.ok) == ("5", True)


@pytest.mark.parametrize(
    "llamada, esperado",
    [
        (LlamadaTool("1", "restar", {}), "No existe la tool"),
        (LlamadaTool("1", "sumar", {"a": 1}), "Faltan argumentos obligatorios: b"),
        (LlamadaTool("1", "sumar", {"_error_argumentos": "x"}), "JSON válido"),
        (LlamadaTool("1", "sumar", {"a": "falla", "b": 1}), "ERROR inesperado"),
    ],
)
def test_registro_convierte_fallos_en_texto(llamada, esperado):
    r = _registro().ejecutar(llamada)
    assert not r.ok
    assert esperado in r.texto


def test_numeros_como_texto_se_convierten_con_cualquier_pandas():
    from lupa.tools.datos_gov import _a_dataframe

    tabla = _a_dataframe([{"valor": "4409.15", "cod_dane": "05001", "nombre": "A"},
                          {"valor": "3757.08", "cod_dane": "76001", "nombre": "B"}])
    assert tabla["valor"].sum() == pytest.approx(8166.23)
    assert tabla["cod_dane"].tolist() == ["05001", "76001"]  # los códigos conservan los ceros
