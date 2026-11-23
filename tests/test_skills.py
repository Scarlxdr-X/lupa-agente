import pytest

from lupa.skills import cargar_skills, catalogo, leer_skill, tool_cargar_skill
from lupa.tools.base import ErrorTool

SKILLS_ESPERADOS = {
    "explorar_datos",
    "analisis_estadistico",
    "visualizacion",
    "investigacion_web",
    "redaccion_informe",
}


def test_carga_los_cinco_skills_del_repositorio():
    skills = cargar_skills()
    assert set(skills) == SKILLS_ESPERADOS
    for skill in skills.values():
        assert skill.descripcion and len(skill.descripcion) < 200
        assert skill.instrucciones.startswith("#")


def test_las_tools_declaradas_existen():
    tools_validas = {"buscar_datasets", "consultar_dataset", "ejecutar_python", "buscar_web", "calculadora"}
    for skill in cargar_skills().values():
        assert set(skill.tools) <= tools_validas, skill.nombre


def test_catalogo_es_una_linea_por_skill():
    assert len(catalogo(cargar_skills()).splitlines()) == 5


def test_tool_cargar_skill_devuelve_instrucciones_y_avisa():
    cargados = []
    tool = tool_cargar_skill(cargar_skills(), cargados.append)
    texto = tool.funcion("explorar_datos")
    assert "32sa-8pi3" in texto  # trae los conjuntos verificados
    assert cargados == ["explorar_datos"]
    assert tool.definicion.parametros["properties"]["nombre"]["enum"]
    with pytest.raises(ErrorTool):
        tool.funcion("no_existe")


def test_skill_sin_encabezado_falla(tmp_path):
    archivo = tmp_path / "SKILL.md"
    archivo.write_text("# Sin encabezado")
    with pytest.raises(ValueError, match="encabezado"):
        leer_skill(archivo)
