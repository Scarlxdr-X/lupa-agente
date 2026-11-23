"""Evaluación de Lupa: corre el banco de tareas con y sin skills y mide.

Como el agente no se entrena, su solidez se demuestra midiendo:
    - Tasa de éxito: tareas cuyas verificaciones pasan todas.
    - Uso correcto de tools: llamadas a tools esperadas (o a cargar_skill) sobre el total.
    - Pasos por tarea, errores de tools y errores recuperados.
    - Tiempo y tokens.

Las respuestas esperadas se calculan en el momento con una consulta directa a
datos.gov.co (ver eval/tareas.json), así no quedan desactualizadas.

    lupa-evaluar                                   # todo, con y sin skills
    lupa-evaluar --tareas S1,M1 --configuraciones con_skills
    lupa-evaluar --pausa 8                         # más espera si la capa gratuita da error 429
    lupa-evaluar --unir eval/resultados/A eval/resultados/B   # junta corridas hechas por partes
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .agent import Agente, Resultado
from .config import Config
from .llm import crear_proveedor
from .tools.calculadora import evaluar as evaluar_expresion
from .tools.datos_gov import ClienteSODA

RAIZ = Path(__file__).resolve().parents[2]
ARCHIVO_TAREAS = RAIZ / "eval" / "tareas.json"
NIVELES = {"simple": "Simples", "varios_pasos": "Varios pasos", "compleja": "Complejas"}
CONFIGURACIONES = {"sin_skills": False, "con_skills": True}


# ---------------------------------------------------------------------------
# Lectura de números en la respuesta del agente
# ---------------------------------------------------------------------------

_NUMERO = re.compile(r"-?\d[\d.,]*")
_ESCALAS = [
    (re.compile(r"^\s*mil\s+millones"), 1e9),
    (re.compile(r"^\s*billones?"), 1e12),
    (re.compile(r"^\s*millones?"), 1e6),
    (re.compile(r"^\s*mil\b"), 1e3),
]


def _a_float(token: str) -> float | None:
    """Interpreta '4.292,27', '4,292.27', '7.006.652', '3881.44' o '1,5'."""
    token = token.rstrip(".,")
    if not token or token == "-":
        return None
    if "." in token and "," in token:
        decimal = "," if token.rfind(",") > token.rfind(".") else "."
        miles = "." if decimal == "," else ","
        token = token.replace(miles, "").replace(decimal, ".")
    elif token.count(".") > 1 or token.count(",") > 1:
        token = token.replace(".", "").replace(",", "")
    elif "." in token or "," in token:
        sep = "." if "." in token else ","
        entero, frac = token.split(sep)
        # Un separador seguido de exactamente 3 dígitos se lee como de miles (7.006 -> 7006)
        token = entero + frac if len(frac) == 3 and entero.lstrip("-") not in ("", "0") else f"{entero}.{frac}"
    try:
        return float(token)
    except ValueError:
        return None


def extraer_numeros(texto: str) -> list[float]:
    """Todos los números del texto, incluidas sus versiones con escala ('483 mil millones')."""
    texto = texto.lower().replace(" ", " ").replace(" ", " ")
    numeros = []
    for m in _NUMERO.finditer(texto):
        valor = _a_float(m.group(0))
        if valor is None:
            continue
        numeros.append(valor)
        resto = texto[m.end() : m.end() + 20]
        for patron, factor in _ESCALAS:
            if patron.match(resto):
                numeros.append(valor * factor)
                break
    return numeros


def contiene_numero(texto: str, esperado: float, tolerancia: float, absoluto: bool = False) -> bool:
    for n in extraer_numeros(texto):
        candidatos = [n, abs(n)] if absoluto else [n]
        objetivo = abs(esperado) if absoluto else esperado
        for c in candidatos:
            if objetivo == 0 and c == 0:
                return True
            if objetivo != 0 and abs(c - objetivo) / abs(objetivo) <= tolerancia:
                return True
    return False


# ---------------------------------------------------------------------------
# Verificaciones
# ---------------------------------------------------------------------------


@dataclass
class Chequeo:
    tipo: str
    ok: bool
    detalle: str


def valor_esperado(cliente: ClienteSODA, verificacion: dict[str, Any]) -> float:
    variables = {}
    for nombre, c in verificacion["consultas"].items():
        params = {"$select": c["select"], "$where": c.get("where"), "$group": c.get("group"),
                  "$order": c.get("order"), "$limit": c.get("limit", 1)}
        filas = cliente.get_json(f"/resource/{c['dataset']}.json", params)
        variables[nombre] = float(filas[0]["v"])
    return evaluar_expresion(verificacion["expresion"], variables)


def verificar(res: Resultado, verificaciones: list[dict[str, Any]], cliente: ClienteSODA) -> list[Chequeo]:
    chequeos = []
    respuesta = res.respuesta or ""
    for v in verificaciones:
        tipo = v["tipo"]
        if tipo == "numero":
            try:
                esperado = valor_esperado(cliente, v)
            except Exception as exc:  # noqa: BLE001
                chequeos.append(Chequeo(tipo, False, f"No se pudo calcular el valor esperado: {exc}"))
                continue
            ok = contiene_numero(respuesta, esperado, v.get("tolerancia", 0.01), v.get("absoluto", False))
            chequeos.append(Chequeo(tipo, ok, f"esperado ≈ {esperado:,.2f}"))
        elif tipo == "contiene":
            faltan = [t for t in v["textos"] if t.lower() not in respuesta.lower()]
            chequeos.append(Chequeo(tipo, not faltan, f"faltan: {faltan}" if faltan else "ok"))
        elif tipo == "grafica":
            chequeos.append(Chequeo(tipo, bool(res.graficas), f"{len(res.graficas)} gráficas"))
        elif tipo == "web":
            ok = "buscar_web" in res.tools_usadas and "http" in respuesta
            chequeos.append(Chequeo(tipo, ok, "usó buscar_web y citó enlaces" if ok else "sin búsqueda web citada"))
        elif tipo == "dataset":
            ids = [
                str((e.argumentos or {}).get("dataset_id", "")).lower()
                for e in res.eventos
                if e.tipo == "llamada" and e.tool == "consultar_dataset"
            ]
            chequeos.append(Chequeo(tipo, v["id"] in ids, f"consultó {sorted(set(ids))}"))
        elif tipo == "tools_exitosas":
            exitosas = {e.tool for e in res.eventos if e.tipo == "resultado" and e.ok}
            faltan = [t for t in v["tools"] if t not in exitosas]
            chequeos.append(Chequeo(tipo, not faltan, f"faltan: {faltan}" if faltan else "ok"))
        else:
            chequeos.append(Chequeo(tipo, False, "tipo de verificación desconocido"))
    return chequeos


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------


@dataclass
class RegistroTarea:
    tarea: str
    nivel: str
    configuracion: str
    exito: bool
    chequeos: list[dict[str, Any]]
    precision_tools: float | None
    pasos: int
    llamadas_llm: int
    tools_usadas: list[str]
    skills_cargados: list[str]
    errores_tool: int
    errores_recuperados: int
    tokens: int
    duracion_s: float
    completo: bool
    error: str | None
    respuesta: str = field(repr=False, default="")


def precision_tools(res: Resultado, esperadas: list[str]) -> float | None:
    usadas = res.tools_usadas
    if not usadas:
        return None
    correctas = sum(1 for t in usadas if t in esperadas or t == "cargar_skill")
    return correctas / len(usadas)


def correr_tarea(tarea: dict, nombre_config: str, config: Config, proveedor: str | None,
                 carpeta: Path, cliente: ClienteSODA) -> RegistroTarea:
    agente = Agente(
        crear_proveedor(config, proveedor),
        config,
        usar_skills=CONFIGURACIONES[nombre_config],
        carpeta_trabajo=carpeta / nombre_config / tarea["id"],
        cliente_soda=cliente,
    )
    res = agente.responder(tarea["pregunta"])
    chequeos = verificar(res, tarea["verificaciones"], cliente)
    return RegistroTarea(
        tarea=tarea["id"],
        nivel=tarea["nivel"],
        configuracion=nombre_config,
        exito=res.error is None and all(c.ok for c in chequeos),
        chequeos=[asdict(c) for c in chequeos],
        precision_tools=precision_tools(res, tarea["tools_esperadas"]),
        pasos=res.pasos,
        llamadas_llm=res.llamadas_llm,
        tools_usadas=res.tools_usadas,
        skills_cargados=res.skills_cargados,
        errores_tool=res.errores_tool,
        errores_recuperados=res.errores_recuperados,
        tokens=res.tokens_entrada + res.tokens_salida,
        duracion_s=round(res.duracion_s, 1),
        completo=res.completo,
        error=res.error,
        respuesta=res.respuesta,
    )


def resumir(registros: list[RegistroTarea]) -> dict[str, dict[str, Any]]:
    resumen: dict[str, dict[str, Any]] = {}
    for nombre in CONFIGURACIONES:
        regs = [r for r in registros if r.configuracion == nombre]
        if not regs:
            continue
        precisiones = [r.precision_tools for r in regs if r.precision_tools is not None]
        fila: dict[str, Any] = {
            "tareas": len(regs),
            "exito_total": sum(r.exito for r in regs) / len(regs),
            "precision_tools": statistics.mean(precisiones) if precisiones else None,
            "pasos_promedio": statistics.mean(r.pasos for r in regs),
            "errores_tool": sum(r.errores_tool for r in regs),
            "errores_recuperados": sum(r.errores_recuperados for r in regs),
            "tiempo_promedio_s": statistics.mean(r.duracion_s for r in regs),
            "tokens_promedio": statistics.mean(r.tokens for r in regs),
        }
        for nivel in NIVELES:
            del_nivel = [r for r in regs if r.nivel == nivel]
            fila[f"exito_{nivel}"] = sum(r.exito for r in del_nivel) / len(del_nivel) if del_nivel else None
        resumen[nombre] = fila
    return resumen


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.0f} %"


def escribir_resumen_md(resumen: dict, registros: list[RegistroTarea], archivo: Path, proveedor: str) -> None:
    nombres = list(resumen)
    titulo = {"sin_skills": "Sin skills", "con_skills": "Con skills"}
    filas = [
        ("Tasa de éxito (total)", lambda r: _pct(r["exito_total"])),
        *[(f"Éxito: {etq.lower()}", lambda r, n=n: _pct(r[f"exito_{n}"])) for n, etq in NIVELES.items()],
        ("Uso correcto de tools", lambda r: _pct(r["precision_tools"])),
        ("Pasos por tarea (promedio)", lambda r: f"{r['pasos_promedio']:.1f}"),
        ("Errores de tools / recuperados", lambda r: f"{r['errores_tool']} / {r['errores_recuperados']}"),
        ("Tiempo por tarea (promedio)", lambda r: f"{r['tiempo_promedio_s']:.0f} s"),
        ("Tokens por tarea (promedio)", lambda r: f"{r['tokens_promedio']:,.0f}"),
    ]
    lineas = [
        f"# Resultados de la evaluación ({datetime.now():%Y-%m-%d %H:%M})",
        "",
        f"Proveedor: {proveedor} · Tareas: {resumen[nombres[0]]['tareas']} por configuración",
        "",
        "| Métrica | " + " | ".join(titulo[n] for n in nombres) + " |",
        "| --- | " + " | ".join("---" for _ in nombres) + " |",
    ]
    for etiqueta, f in filas:
        lineas.append(f"| {etiqueta} | " + " | ".join(f(resumen[n]) for n in nombres) + " |")
    lineas += ["", "## Detalle por tarea", "", "| Tarea | Configuración | Éxito | Pasos | Tools | Chequeos |",
               "| --- | --- | --- | --- | --- | --- |"]
    for r in registros:
        chequeos = "; ".join(f"{c['tipo']}: {'ok' if c['ok'] else 'falla'} ({c['detalle']})" for c in r.chequeos)
        lineas.append(
            f"| {r.tarea} | {titulo[r.configuracion]} | {'sí' if r.exito else 'no'} | {r.pasos} | "
            f"{', '.join(r.tools_usadas)} | {chequeos} |"
        )
    archivo.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def graficar(resumen: dict, archivo: Path) -> None:
    """Barras agrupadas: tasa de éxito por nivel, sin skills (gris) contra con skills (azul)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    etiquetas = [*NIVELES.values(), "Total"]
    claves = [*(f"exito_{n}" for n in NIVELES), "exito_total"]
    estilos = {"sin_skills": ("Sin skills", "#a8a69f"), "con_skills": ("Con skills", "#2a78d6")}
    presentes = [n for n in estilos if n in resumen]

    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    ancho = 0.36
    for i, nombre in enumerate(presentes):
        valores = [(resumen[nombre][k] or 0) * 100 for k in claves]
        posiciones = [x + (i - (len(presentes) - 1) / 2) * (ancho + 0.02) for x in range(len(claves))]
        etiqueta, color = estilos[nombre]
        barras = ax.bar(posiciones, valores, width=ancho, color=color, label=etiqueta, zorder=2)
        for barra, v in zip(barras, valores, strict=True):
            ax.text(barra.get_x() + barra.get_width() / 2, v + 1.5, f"{v:.0f}%", ha="center",
                    va="bottom", fontsize=9, color="#52514e")
    ax.set_xticks(range(len(claves)), etiquetas)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Tareas resueltas (%)", color="#52514e")
    ax.set_title("Tasa de éxito por nivel de dificultad", loc="left", fontsize=12, color="#0b0b0b", pad=30)
    ax.grid(axis="y", color="#e6e5e1", zorder=0)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#c9c8c2")
    ax.tick_params(colors="#52514e", length=0)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncols=2, borderaxespad=0.2)
    fig.tight_layout()
    fig.savefig(archivo)
    plt.close(fig)


def unir_resultados(carpetas: list[Path], destino: Path, proveedor: str) -> dict[str, dict[str, Any]]:
    """Junta los resultados.json de varias corridas parciales en un solo resumen.

    La capa gratuita del LLM limita las peticiones por día, así que la
    evaluación completa suele correrse por partes. Si una misma tarea y
    configuración aparece en varias corridas, gana la más reciente.
    """
    por_clave: dict[tuple[str, str], RegistroTarea] = {}
    for carpeta in sorted(Path(c) for c in carpetas):
        archivo = carpeta / "resultados.json"
        if not archivo.exists():
            raise FileNotFoundError(f"No encontré {archivo}")
        for dato in json.loads(archivo.read_text(encoding="utf-8")):
            registro = RegistroTarea(**dato)
            por_clave[(registro.configuracion, registro.tarea)] = registro
    registros = sorted(por_clave.values(), key=lambda r: (r.configuracion, r.tarea))

    destino.mkdir(parents=True, exist_ok=True)
    (destino / "resultados.json").write_text(
        json.dumps([asdict(r) for r in registros], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    resumen = resumir(registros)
    (destino / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    escribir_resumen_md(resumen, registros, destino / "resumen.md", proveedor)
    graficar(resumen, destino / "exito_por_nivel.png")
    return resumen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evalúa Lupa con y sin skills.")
    parser.add_argument("--tareas", help="Ids separados por coma (por defecto, todas).")
    parser.add_argument("--configuraciones", nargs="+", choices=list(CONFIGURACIONES), default=list(CONFIGURACIONES))
    parser.add_argument("--proveedor", choices=["gemini", "openai_compat"], help="Por defecto, LUPA_PROVEEDOR.")
    parser.add_argument("--pausa", type=float, default=5, help="Segundos entre tareas (evita el error 429).")
    parser.add_argument("--archivo", type=Path, default=ARCHIVO_TAREAS)
    parser.add_argument("--unir", nargs="+", type=Path, metavar="CARPETA",
                        help="No corre tareas: junta los resultados de varias corridas parciales.")
    args = parser.parse_args(argv)

    config = Config.cargar()
    proveedor = args.proveedor or config.proveedor

    if args.unir:
        destino = RAIZ / "eval" / "resultados" / f"combinado-{datetime.now():%Y%m%d-%H%M%S}"
        unir_resultados(args.unir, destino, proveedor)
        print(f"Listo. Resultados combinados en {destino}")
        print((destino / "resumen.md").read_text(encoding="utf-8").split("## Detalle")[0])
        return 0
    tareas = json.loads(args.archivo.read_text(encoding="utf-8"))["tareas"]
    if args.tareas:
        ids = {t.strip() for t in args.tareas.split(",")}
        tareas = [t for t in tareas if t["id"] in ids]

    carpeta = RAIZ / "eval" / "resultados" / f"{datetime.now():%Y%m%d-%H%M%S}"
    carpeta.mkdir(parents=True, exist_ok=True)
    cliente = ClienteSODA(
        app_token=config.soda_app_token,
        carpeta_cache=Path(config.carpeta_cache) / "datos_gov",
        horas_cache=config.horas_cache,
    )

    registros: list[RegistroTarea] = []
    total = len(tareas) * len(args.configuraciones)
    for nombre_config in args.configuraciones:
        for tarea in tareas:
            print(f"[{len(registros) + 1}/{total}] {nombre_config} · {tarea['id']}: {tarea['pregunta'][:70]}…", flush=True)
            registro = correr_tarea(tarea, nombre_config, config, proveedor, carpeta, cliente)
            registros.append(registro)
            estado = "OK   " if registro.exito else "FALLA"
            print(f"      {estado} {registro.pasos} pasos · {registro.duracion_s:.0f} s · {registro.chequeos}", flush=True)
            # Se guarda después de cada tarea: si algo se corta, no se pierde lo hecho
            (carpeta / "resultados.json").write_text(
                json.dumps([asdict(r) for r in registros], ensure_ascii=False, indent=2), encoding="utf-8"
            )
            time.sleep(args.pausa)

    resumen = resumir(registros)
    (carpeta / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    escribir_resumen_md(resumen, registros, carpeta / "resumen.md", proveedor)
    graficar(resumen, carpeta / "exito_por_nivel.png")
    print(f"\nListo. Resultados en {carpeta}")
    print((carpeta / "resumen.md").read_text(encoding="utf-8").split("## Detalle")[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
