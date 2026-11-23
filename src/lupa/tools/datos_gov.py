"""Tools para el portal de datos abiertos de Colombia (datos.gov.co).

Usan dos APIs públicas de la plataforma Socrata, que no necesitan clave:
    - Catálogo:  https://www.datos.gov.co/api/catalog/v1?q=...
    - Datos:     https://www.datos.gov.co/resource/<id>.json?$select=...&$where=...

Las consultas usan SoQL, un SQL simplificado. Lo importante es que la API
agrega en el servidor (sum, avg, count, date_trunc_ym...), así que se puede
resumir un conjunto de millones de filas sin descargarlo.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from ..llm.base import DefinicionTool
from .base import Contexto, ErrorTool, Fuente, Tool, entero

URL_BASE = "https://www.datos.gov.co"
PATRON_ID = re.compile(r"^[a-z0-9]{4}-[a-z0-9]{4}$")

# Columnas con datos personales (cédulas, cuentas bancarias, nombres de
# funcionarios, direcciones, fechas de nacimiento...). Se buscan por nombre.
PATRON_PERSONAL = re.compile(
    r"(documento|identificaci|c_dula|cedula|n_mero_de_cuenta|numero_de_cuenta|tipo_de_cuenta|nombre_del_banco"
    r"|supervisor|ordenador|representante_legal|direcci|domicilio|tel_fono|telefono|correo|email"
    r"|fechanacimiento|fecha_de_nacimiento|fecha_nacimiento)"
)
# Excepción: "documentos_tipo" habla de pliegos tipo, no de personas.
EXCEPCIONES_PERSONAL = {"documentos_tipo", "descripcion_documentos_tipo"}


def es_columna_personal(nombre: str) -> bool:
    nombre = nombre.lower()
    return nombre not in EXCEPCIONES_PERSONAL and bool(PATRON_PERSONAL.search(nombre))


def columnas_personales_en(clausula: str) -> list[str]:
    """Identificadores con datos personales dentro de una cláusula SoQL.
    Se ignora el texto entre comillas, para no bloquear un filtro como
    like '%CUENTA%'."""
    sin_literales = re.sub(r"'(?:[^']|'')*'", "''", clausula or "")
    identificadores = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", sin_literales)
    return sorted({i for i in identificadores if es_columna_personal(i)})


# ---------------------------------------------------------------------------
# Cliente HTTP con caché
# ---------------------------------------------------------------------------


class ClienteSODA:
    """Hace las peticiones a datos.gov.co y guarda las respuestas en disco.

    La caché hace que repetir una pregunta (por ejemplo en la demo o en la
    evaluación) no dependa de que la API esté rápida ese día.
    """

    def __init__(
        self,
        app_token: str | None = None,
        carpeta_cache: Path | None = Path("cache") / "datos_gov",
        horas_cache: float = 24,
        timeout_s: float = 60,
        sesion: requests.Session | None = None,
    ) -> None:
        self.app_token = app_token
        self.carpeta_cache = Path(carpeta_cache) if carpeta_cache else None
        self.horas_cache = horas_cache
        self.timeout_s = timeout_s
        self.sesion = sesion or requests.Session()

    def get_json(self, ruta: str, params: dict[str, Any]) -> Any:
        params = {k: v for k, v in params.items() if v not in (None, "")}
        archivo = self._archivo_cache(ruta, params)
        if archivo and archivo.exists() and (time.time() - archivo.stat().st_mtime) < self.horas_cache * 3600:
            return json.loads(archivo.read_text(encoding="utf-8"))

        datos = self._pedir(ruta, params)
        if archivo:
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        return datos

    def _pedir(self, ruta: str, params: dict[str, Any], reintentos: int = 2) -> Any:
        headers = {"X-App-Token": self.app_token} if self.app_token else {}
        for intento in range(reintentos + 1):
            try:
                # Pasar `params` como diccionario hace que requests codifique % y
                # espacios; armar la URL a mano rompe filtros como like '%VALLE%'.
                r = self.sesion.get(URL_BASE + ruta, params=params, headers=headers, timeout=self.timeout_s)
            except requests.Timeout as exc:
                raise ErrorTool(
                    f"datos.gov.co tardó más de {self.timeout_s:.0f} s. Agrega filtros en `where` "
                    "o agrupa en el servidor con `select` + `group` para reducir el trabajo."
                ) from exc
            except requests.RequestException as exc:
                raise ErrorTool(f"No se pudo conectar con datos.gov.co: {exc}") from exc

            if r.status_code in (429, 500, 502, 503) and intento < reintentos:
                time.sleep(2 * (intento + 1))
                continue
            if r.status_code >= 400:
                raise ErrorTool(f"datos.gov.co rechazó la consulta (HTTP {r.status_code}): {_mensaje_error(r)}")
            return r.json()
        raise ErrorTool("datos.gov.co no respondió después de varios intentos.")  # pragma: no cover

    def _archivo_cache(self, ruta: str, params: dict[str, Any]) -> Path | None:
        if not self.carpeta_cache or self.horas_cache <= 0:
            return None
        clave = json.dumps([ruta, sorted(params.items())], ensure_ascii=False, default=str)
        return self.carpeta_cache / f"{hashlib.sha1(clave.encode()).hexdigest()}.json"


def _mensaje_error(respuesta: requests.Response) -> str:
    try:
        cuerpo = respuesta.json()
        return str(cuerpo.get("message") or cuerpo)[:600]
    except ValueError:
        return respuesta.text[:600]


# ---------------------------------------------------------------------------
# buscar_datasets
# ---------------------------------------------------------------------------

DEF_BUSCAR = DefinicionTool(
    nombre="buscar_datasets",
    descripcion=(
        "Busca conjuntos de datos en el catálogo de datos.gov.co (portal de datos abiertos de Colombia). "
        "Acepta palabras clave en español (por ejemplo 'contratos secop', 'tasa de cambio') o el id de un "
        "conjunto ('32sa-8pi3'). Devuelve id, nombre, entidad, fecha de actualización y las columnas con su "
        "tipo y descripción. Úsala antes de consultar un conjunto cuyas columnas no conoces."
    ),
    parametros={
        "type": "object",
        "properties": {
            "consulta": {"type": "string", "description": "Palabras clave o id del conjunto (formato xxxx-xxxx)."},
            "limite": {"type": "integer", "description": "Cuántos resultados devolver (1 a 8). Por defecto 5."},
        },
        "required": ["consulta"],
    },
)


def buscar_datasets(cliente: ClienteSODA, consulta: str, limite: int = 5) -> str:
    consulta = consulta.strip()
    limite = entero(limite, 5, 1, 8)
    params: dict[str, Any] = {"domains": "www.datos.gov.co", "only": "dataset", "limit": limite}
    if PATRON_ID.match(consulta.lower()):
        params["ids"] = consulta.lower()
    else:
        params["q"] = consulta

    datos = cliente.get_json("/api/catalog/v1", params)
    resultados = datos.get("results", [])
    if not resultados:
        return f"No encontré conjuntos para '{consulta}'. Prueba con otras palabras (más generales o sinónimos)."

    lineas = [f"Encontré {len(resultados)} de {datos.get('resultSetSize', len(resultados))} conjuntos para '{consulta}':"]
    for i, item in enumerate(resultados, 1):
        lineas.append("")
        lineas.extend(_describir_recurso(i, item.get("resource", {})))
    lineas.append("")
    lineas.append("Las columnas de tipo Text que guardan números se convierten en SoQL con ::number, ej. avg(col::number).")
    return "\n".join(lineas)


def _describir_recurso(i: int, rec: dict[str, Any]) -> list[str]:
    id_ = rec.get("id", "")
    actualizado = (rec.get("data_updated_at") or rec.get("updatedAt") or "")[:10]
    descripcion = " ".join((rec.get("description") or "").split())[:300]
    lineas = [
        f"{i}. {rec.get('name', '(sin nombre)')}",
        f"   id: {id_} · entidad: {rec.get('attribution') or 'sin dato'} · datos actualizados: {actualizado}",
        f"   enlace: {URL_BASE}/d/{id_}",
        f"   descripción: {descripcion}",
    ]
    nombres = rec.get("columns_field_name") or []
    tipos = rec.get("columns_datatype") or []
    descripciones = rec.get("columns_description") or []
    columnas = []
    for j, nombre in enumerate(nombres[:45]):
        tipo = tipos[j] if j < len(tipos) else "?"
        if es_columna_personal(nombre):
            columnas.append(f"{nombre} [bloqueada: dato personal]")
            continue
        desc = " ".join((descripciones[j] if j < len(descripciones) else "").split())[:70]
        columnas.append(f"{nombre} ({tipo}{': ' + desc if desc else ''})")
    extra = f" (+{len(nombres) - 45} más)" if len(nombres) > 45 else ""
    lineas.append(f"   columnas ({len(nombres)}){extra}: " + "; ".join(columnas))
    return lineas


# ---------------------------------------------------------------------------
# consultar_dataset
# ---------------------------------------------------------------------------

DEF_CONSULTAR = DefinicionTool(
    nombre="consultar_dataset",
    descripcion=(
        "Consulta un conjunto de datos.gov.co con SoQL y guarda el resultado como CSV en la carpeta de trabajo "
        "(tabla_1.csv, tabla_2.csv...) para analizarlo con ejecutar_python. Devuelve las primeras filas. "
        "Agrega en el servidor siempre que puedas, ej. select='departamento, sum(valor_del_contrato) AS total', "
        "group='departamento'. Fechas: where=\"fecha_de_firma between '2025-01-01T00:00:00' and "
        "'2025-12-31T23:59:59'\". Textos: upper(col) like '%VALLE%'. Las columnas con datos personales "
        "(cédulas, cuentas bancarias, supervisores) están bloqueadas."
    ),
    parametros={
        "type": "object",
        "properties": {
            "dataset_id": {"type": "string", "description": "Id del conjunto, formato xxxx-xxxx."},
            "select": {"type": "string", "description": "Columnas o agregaciones ($select). Vacío = todas."},
            "where": {"type": "string", "description": "Filtro SoQL ($where)."},
            "group": {"type": "string", "description": "Columnas para agrupar ($group)."},
            "order": {"type": "string", "description": "Orden, ej. 'total DESC' ($order)."},
            "limit": {"type": "integer", "description": "Máximo de filas (1 a 5000). Por defecto 1000."},
        },
        "required": ["dataset_id"],
    },
)


def consultar_dataset(
    cliente: ClienteSODA,
    contexto: Contexto,
    dataset_id: str,
    select: str | None = None,
    where: str | None = None,
    group: str | None = None,
    order: str | None = None,
    limit: int = 1000,
) -> str:
    dataset_id = (dataset_id or "").strip().lower()
    if not PATRON_ID.match(dataset_id):
        raise ErrorTool(f"'{dataset_id}' no es un id válido. Debe tener el formato xxxx-xxxx (ej. 32sa-8pi3).")

    bloqueadas = sorted(set().union(*(columnas_personales_en(c or "") for c in (select, where, group, order))))
    if bloqueadas:
        raise ErrorTool(
            f"La consulta usa columnas con datos personales ({', '.join(bloqueadas)}), que Lupa no consulta. "
            "Reformula la consulta sin ellas."
        )

    limit = entero(limit, 1000, 1, 5000)
    params = {"$select": select, "$where": where, "$group": group, "$order": order, "$limit": limit}
    filas = cliente.get_json(f"/resource/{dataset_id}.json", params)
    if not isinstance(filas, list):
        raise ErrorTool(f"Respuesta inesperada de datos.gov.co: {str(filas)[:300]}")

    tabla = _a_dataframe(filas)
    omitidas = [c for c in tabla.columns if es_columna_personal(c)]
    tabla = tabla.drop(columns=omitidas)

    nombre_archivo = contexto.nombre_nueva_tabla()
    tabla.to_csv(contexto.carpeta / nombre_archivo, index=False)
    contexto.agregar_fuente(
        Fuente(tipo="dataset", titulo=_titulo_dataset(cliente, dataset_id), url=f"{URL_BASE}/d/{dataset_id}")
    )

    if tabla.empty:
        return (
            f"La consulta a {dataset_id} no devolvió filas (se guardó vacía como {nombre_archivo}). "
            "Revisa el filtro: mayúsculas y tildes, formato de fechas o valores exactos de las categorías."
        )

    tipos = ", ".join(f"{c} ({'número' if pd.api.types.is_numeric_dtype(t) else 'texto'})" for c, t in tabla.dtypes.items())
    lineas = [
        f"Consulta a {dataset_id}: {len(tabla)} filas × {len(tabla.columns)} columnas. "
        f"Guardada como {nombre_archivo} (en ejecutar_python: pd.read_csv('{nombre_archivo}')).",
        f"Columnas: {tipos}",
    ]
    if omitidas:
        lineas.append(f"Se omitieron {len(omitidas)} columnas con datos personales.")
    if len(tabla) >= limit:
        lineas.append(f"AVISO: se alcanzó el límite de {limit} filas; puede haber más. Filtra o agrupa en el servidor.")
    muestra = tabla.iloc[:20, :15]
    lineas.append(f"Primeras {len(muestra)} filas{' (15 primeras columnas)' if tabla.shape[1] > 15 else ''}:")
    lineas.append(muestra.to_csv(index=False).strip())
    return "\n".join(lineas)


def _a_dataframe(filas: list[dict[str, Any]]) -> pd.DataFrame:
    """Convierte la respuesta JSON en tabla. La API manda los números como
    texto ("4292.27"), así que se convierten las columnas que son 100 % numéricas,
    menos los códigos (DANE, NIT...), que perderían los ceros a la izquierda."""
    limpias = [{k: (v.get("url", json.dumps(v)) if isinstance(v, dict) else v) for k, v in f.items()} for f in filas]
    tabla = pd.DataFrame(limpias)
    for col in tabla.columns:
        # pandas 2 guarda el texto como `object`; pandas 3, como `str`. Se revisan ambos.
        es_texto = tabla[col].dtype == object or pd.api.types.is_string_dtype(tabla[col])
        if col.startswith(("cod", "nit", "id_")) or not es_texto:
            continue
        convertida = pd.to_numeric(tabla[col], errors="coerce")
        if convertida.notna().sum() == tabla[col].notna().sum() and tabla[col].notna().any():
            tabla[col] = convertida
    return tabla


_titulos: dict[str, str] = {}


def _titulo_dataset(cliente: ClienteSODA, dataset_id: str) -> str:
    """Nombre del conjunto para citarlo. Si el catálogo falla, se usa el id."""
    if dataset_id not in _titulos:
        try:
            datos = cliente.get_json("/api/catalog/v1", {"ids": dataset_id, "domains": "www.datos.gov.co"})
            _titulos[dataset_id] = datos["results"][0]["resource"]["name"]
        except Exception:  # noqa: BLE001 - el título es un adorno, nunca debe romper la consulta
            return f"Conjunto {dataset_id}"
    return f"{_titulos[dataset_id]} ({dataset_id})"


# ---------------------------------------------------------------------------
# Fábricas
# ---------------------------------------------------------------------------


def tool_buscar_datasets(cliente: ClienteSODA) -> Tool:
    def funcion(consulta: str, limite: int = 5) -> str:
        return buscar_datasets(cliente, consulta, limite)

    return Tool(DEF_BUSCAR, funcion)


def tool_consultar_dataset(cliente: ClienteSODA, contexto: Contexto) -> Tool:
    def funcion(
        dataset_id: str,
        select: str | None = None,
        where: str | None = None,
        group: str | None = None,
        order: str | None = None,
        limit: int = 1000,
    ) -> str:
        return consultar_dataset(cliente, contexto, dataset_id, select, where, group, order, limit)

    return Tool(DEF_CONSULTAR, funcion)
