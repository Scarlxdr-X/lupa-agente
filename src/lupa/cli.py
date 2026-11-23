"""Hacerle una pregunta a Lupa desde la terminal y ver cada paso.

    lupa-preguntar "¿Cuál fue la TRM promedio de octubre de 2025?"
    lupa-preguntar --sin-skills --proveedor openai_compat "..."
"""

from __future__ import annotations

import argparse
import json

from .agent import Agente
from .config import Config
from .llm import crear_proveedor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pregúntale a Lupa desde la terminal.")
    parser.add_argument("pregunta")
    parser.add_argument("--proveedor", choices=["gemini", "openai_compat"])
    parser.add_argument("--sin-skills", action="store_true")
    args = parser.parse_args(argv)

    config = Config.cargar()
    agente = Agente(crear_proveedor(config, args.proveedor), config, usar_skills=not args.sin_skills)
    print(f"Carpeta de trabajo: {agente.contexto.carpeta}\n")

    for evento in agente.responder_por_pasos(args.pregunta):
        if evento.tipo == "llamada":
            print(f"[paso {evento.paso}] -> {evento.tool}({json.dumps(evento.argumentos, ensure_ascii=False)[:300]})")
        elif evento.tipo == "resultado":
            marca = "ok   " if evento.ok else "ERROR"
            print(f"           {marca} {evento.texto[:300].replace(chr(10), ' ')}")
        elif evento.tipo == "pensamiento":
            print(f"[paso {evento.paso}] {evento.texto[:300]}")
        elif evento.tipo in ("aviso", "error"):
            print(f"[{evento.tipo}] {evento.texto}")

    res = agente.ultimo_resultado
    print("\n" + "=" * 70 + f"\n{res.respuesta}\n" + "=" * 70)
    print(
        f"Pasos: {res.pasos} · Llamadas al LLM: {res.llamadas_llm} · Tokens: {res.tokens_entrada + res.tokens_salida:,}"
        f" · Tiempo: {res.duracion_s:.1f} s · Skills: {', '.join(res.skills_cargados) or 'ninguno'}"
    )
    for g in res.graficas:
        print(f"Gráfica: {g}")
    return 0 if res.error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
