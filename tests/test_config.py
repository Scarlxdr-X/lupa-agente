import pytest

from lupa.config import Config


def test_valores_por_defecto(entorno_limpio):
    config = Config.cargar()
    assert config.proveedor == "gemini"
    assert config.gemini_api_key is None
    assert config.openai_base_url == "https://api.groq.com/openai/v1"
    assert config.max_pasos == 15


def test_lee_archivo_env(entorno_limpio, tmp_path):
    env = tmp_path / ".env"
    env.write_text("LUPA_PROVEEDOR=openai_compat\nGROQ_API_KEY=gsk_prueba1234\nLUPA_MAX_PASOS=8\n")
    config = Config.cargar(env)
    assert config.proveedor == "openai_compat"
    assert config.openai_api_key == "gsk_prueba1234"
    assert config.max_pasos == 8


def test_variable_de_entorno_gana_al_env(entorno_limpio, tmp_path):
    env = tmp_path / ".env"
    env.write_text("LUPA_MODELO_GEMINI=desde-archivo\n")
    entorno_limpio.setenv("LUPA_MODELO_GEMINI", "desde-entorno")
    assert Config.cargar(env).modelo_gemini == "desde-entorno"


def test_clave_vacia_cuenta_como_ausente(entorno_limpio):
    entorno_limpio.setenv("GEMINI_API_KEY", "")
    assert Config.cargar().gemini_api_key is None


def test_proveedor_invalido(entorno_limpio):
    entorno_limpio.setenv("LUPA_PROVEEDOR", "chatgpt")
    with pytest.raises(ValueError, match="no es válido"):
        Config.cargar()


def test_max_pasos_invalido(entorno_limpio):
    entorno_limpio.setenv("LUPA_MAX_PASOS", "muchos")
    with pytest.raises(ValueError, match="entero"):
        Config.cargar()


def test_resumen_no_expone_claves(entorno_limpio):
    entorno_limpio.setenv("GEMINI_API_KEY", "AIzaSECRETO-abcd")
    resumen = " ".join(Config.cargar().resumen().values())
    assert "SECRETO" not in resumen
    assert "…abcd" in resumen
