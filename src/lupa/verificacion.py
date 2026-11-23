"""Verifica que las claves funcionan y que el LLM sabe usar tools.

Se ejecuta con cualquiera de estas formas:
    lupa-verificar                      (después de pip install -e .)
    python scripts/verificar_conexion.py
    En Colab: from lupa.verificacion import main; main([])

Hace dos pruebas por proveedor:
    1. Texto simple: el LLM responde.
    2. Ida y vuelta con una tool: el LLM pide `multiplicar`, nosotros la
       ejecutamos, le devolvemos el resultado y él responde con la cifra.
       Es exactamente lo que hará el ciclo del agente en la fase 3.
"""

from __future__ import annotations

import argparse
import logging
import re

from .config import Config
from .llm import DefinicionTool, ErrorLLM, Mensaje, ProveedorLLM, crear_proveedor

OK = "[OK]   "
FALLA = "[FALLA]"

TOOL_MULTIPLICAR = DefinicionTool(
    nombre="multiplicar",
    descripcion="Multiplica dos números enteros y devuelve el producto exacto.",
    parametros={
        "type": "object",
        "properties": {
            "a": {"type": "integer", "description": "Primer factor"},
            "b": {"type": "integer", "description": "Segundo factor"},
        },
        "required": ["a", "b"],
    },
)
SISTEMA_PRUEBA = (
    "Eres un asistente de prueba. Para cualquier multiplicación usa siempre la tool "
    "`multiplicar`; nunca calcules de memoria. Responde en español y en una sola frase."
)
PREGUNTA_PRUEBA = "¿Cuánto es 1234 multiplicado por 5678?"
RESULTADO_ESPERADO = str(1234 * 5678)  # 7006652


def _solo_digitos(texto: str) -> str:
    """Quita separadores de miles para comparar cifras ('7.006.652' -> '7006652')."""
    return re.sub(r"(?<=\d)[.,\s  ](?=\d{3})", "", texto)


def prueba_texto(llm: ProveedorLLM) -> bool:
    respuesta = llm.generar([Mensaje.usuario("Responde únicamente con la palabra: listo")])
    ok = "listo" in respuesta.texto.lower()
    estado = OK if ok else FALLA
    print(f"  {estado} Texto simple ({respuesta.duracion_s:.1f} s): {respuesta.texto.strip()[:80]!r}")
    return ok


def prueba_tools(llm: ProveedorLLM) -> bool:
    mensajes = [Mensaje.usuario(PREGUNTA_PRUEBA)]
    tools = [TOOL_MULTIPLICAR]

    # Vuelta 1: el LLM debería pedir la tool
    r1 = llm.generar(mensajes, tools=tools, sistema=SISTEMA_PRUEBA)
    if not r1.pide_tools:
        print(f"  {FALLA} El LLM no pidió la tool; respondió: {r1.texto.strip()[:120]!r}")
        return False
    llamada = r1.llamadas[0]
    print(f"  {OK} El LLM pidió {llamada.nombre}({llamada.argumentos})")

    # Ejecutamos cada tool pedida y devolvemos el resultado
    mensajes.append(r1.mensaje)
    for ll in r1.llamadas:
        try:
            resultado = str(int(ll.argumentos["a"]) * int(ll.argumentos["b"]))
        except (KeyError, TypeError, ValueError) as exc:
            resultado = f"Error: argumentos inválidos ({exc})"
        mensajes.append(Mensaje.resultado_tool(ll, resultado))

    # Vuelta 2: el LLM debería responder usando el resultado
    r2 = llm.generar(mensajes, tools=tools, sistema=SISTEMA_PRUEBA)
    ok = RESULTADO_ESPERADO in _solo_digitos(r2.texto)
    estado = OK if ok else FALLA
    print(f"  {estado} Respuesta final: {r2.texto.strip()[:120]!r}")
    tokens = r1.uso.tokens_entrada + r1.uso.tokens_salida + r2.uso.tokens_entrada + r2.uso.tokens_salida
    print(f"          Tiempo total {r1.duracion_s + r2.duracion_s:.1f} s · {tokens} tokens")
    return ok


def verificar(nombre: str, config: Config, listar_modelos: bool) -> bool:
    print(f"\n== Proveedor: {nombre} ==")
    try:
        llm = crear_proveedor(config, nombre)
    except ErrorLLM as exc:
        print(f"  {FALLA} {exc}")
        return False
    print(f"  Modelo: {llm.modelo}")

    if listar_modelos and hasattr(llm, "listar_modelos"):
        try:
            modelos = llm.listar_modelos()
            print(f"  Modelos disponibles para tu clave ({len(modelos)}):")
            for m in modelos:
                print(f"    - {m}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {FALLA} No se pudieron listar los modelos: {exc}")

    try:
        ok = prueba_texto(llm) and prueba_tools(llm)
    except Exception as exc:  # noqa: BLE001 - mostramos cualquier error de la API
        print(f"  {FALLA} {type(exc).__name__}: {exc}")
        return False
    if getattr(llm, "modelos", None) and llm.modelo != llm.modelos[0]:
        print(f"  Aviso: {llm.modelos[0]} no respondió; se usó el modelo de respaldo {llm.modelo}.")
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifica la conexión de Lupa con los LLM.")
    parser.add_argument(
        "--proveedor",
        choices=["gemini", "openai_compat", "todos"],
        help="Proveedor a probar (por defecto, el de LUPA_PROVEEDOR).",
    )
    parser.add_argument("--listar-modelos", action="store_true", help="Lista los modelos de Gemini disponibles.")
    parser.add_argument("--env", default=None, help="Ruta a un archivo .env (por defecto, ./.env).")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="  %(levelname)s %(message)s")
    config = Config.cargar(args.env)

    print("Configuración:")
    for clave, valor in config.resumen().items():
        print(f"  {clave}: {valor}")

    nombres = ["gemini", "openai_compat"] if args.proveedor == "todos" else [args.proveedor or config.proveedor]
    resultados = {n: verificar(n, config, args.listar_modelos) for n in nombres}

    print("\nResumen:")
    for nombre, ok in resultados.items():
        print(f"  {OK if ok else FALLA} {nombre}")
    return 0 if all(resultados.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
