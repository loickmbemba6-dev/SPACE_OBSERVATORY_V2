# -*- coding: utf-8 -*-
"""SPACE OBSERVATORY — Streamlit interface over an existing read-only SQLite catalogue."""
from __future__ import annotations

import csv
import math
import re
import sqlite3
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SPACE OBSERVATORY",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
DB_URL = "https://github.com/loickmbemba6-dev/SPACE_OBSERVATORY_V2/releases/download/v1.0.0/supernovae_complet.db"
DB_FILE = Path(__file__).resolve().parent / "supernovae_complet.db"
ROCHESTER_DB_FILE = APP_DIR / "rochester_2023_2026.sqlite"
# Optional override for deployment or a different local location:
# set SPACE_OBSERVATORY_DB=D:\\path\\to\\supernovae_complet.db
import os
if os.environ.get("SPACE_OBSERVATORY_DB"):
    DB_FILE = Path(os.environ["SPACE_OBSERVATORY_DB"]).expanduser().resolve()
elif not DB_FILE.is_file():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_db = DB_FILE.with_suffix(DB_FILE.suffix + ".download")
    try:
        urllib.request.urlretrieve(DB_URL, temp_db)
        os.replace(temp_db, DB_FILE)
    finally:
        if temp_db.exists():
            temp_db.unlink()

TABLE = "supernovae"
PAGE_SIZES = [25, 50, 100, 250]
CSV_MAX_BYTES = 50 * 1024 * 1024
CSV_BATCH_SIZE = 2000
NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")

# -----------------------------------------------------------------------------
# Translations — scientific catalogue values are never translated.
# -----------------------------------------------------------------------------
TEXT = {
    "EN": {
        "subtitle": "Explore the supernova universe",
        "language": "Language",
        "navigation": "Navigation",
        "dashboard": "Dashboard",
        "catalogue": "Catalogue",
        "analysis": "Scientific Analysis",
        "about": "About",
        "overview": "A window into the supernova universe",
        "total": "Catalogue records",
        "types": "Distinct reported types",
        "redshifts": "Valid redshift values",
        "photometry": "Photometric measurements",
        "top_types": "Most frequent reported types",
        "discoveries": "Discoveries by year",
        "redshift_dist": "Redshift distribution (sample)",
        "search": "Search name, alias, host or type",
        "search_hint": "For example: SN1990I",
        "type_filter": "Reported type",
        "all_types": "All types",
        "redshift_filter": "Enable maximum redshift filter",
        "max_redshift": "Maximum redshift",
        "rows_per_page": "Rows per page",
        "page": "Page",
        "of": "of",
        "records_found": "Matching records",
        "no_records": "No records match these filters.",
        "results": "Results",
        "details": "Record details",
        "choose_record": "Choose a record (row identity is preserved)",
        "export": "Prepare CSV export (all columns)",
        "export_ready": "CSV export is ready.",
        "export_too_large": "The export exceeds the 50 MiB safety limit. Narrow the filters and try again.",
        "export_error": "CSV export could not be prepared: ",
        "redshift_stats": "Redshift statistics",
        "mean": "Mean",
        "median": "Median",
        "minimum": "Minimum",
        "maximum": "Maximum",
        "missing": "Missing values by column",
        "missing_note": "Missing means NULL, empty text or whitespace-only text.",
        "column": "Column",
        "missing_count": "Missing values",
        "missing_pct": "Missing (%)",
        "database_info": "Database information",
        "database_file": "Database file",
        "table": "Table",
        "records": "Records",
        "columns": "Columns",
        "mode": "Access mode",
        "readonly": "Read-only (database is not modified)",
        "about_text": "SPACE OBSERVATORY is an interface for exploring the existing supernova catalogue. It reads the SQLite database without changing its scientific records.",
        "db_missing": "Database file not found: ",
        "schema_error": "The database does not contain the required table or columns: ",
        "load_error": "Could not open the database: ",
        "all_records": "All catalogue records",
        "record_id": "Internal row ID",
        "footer": "Scientific values and source records are displayed as stored in the database.",
        "no_redshift": "No valid numeric redshift values are available.",
        "year_unknown": "Unknown year",
    },
    "FR": {
        "subtitle": "Explorez l’univers des supernovae",
        "language": "Langue",
        "navigation": "Navigation",
        "dashboard": "Tableau de bord",
        "catalogue": "Catalogue",
        "analysis": "Analyse scientifique",
        "about": "À propos",
        "overview": "Une fenêtre sur l’univers des supernovae",
        "total": "Enregistrements du catalogue",
        "types": "Types déclarés distincts",
        "redshifts": "Valeurs de redshift valides",
        "photometry": "Mesures photométriques",
        "top_types": "Types déclarés les plus fréquents",
        "discoveries": "Découvertes par année",
        "redshift_dist": "Distribution du redshift (échantillon)",
        "search": "Rechercher un nom, alias, hôte ou type",
        "search_hint": "Par exemple : SN1990I",
        "type_filter": "Type déclaré",
        "all_types": "Tous les types",
        "redshift_filter": "Activer le filtre de redshift maximal",
        "max_redshift": "Redshift maximal",
        "rows_per_page": "Lignes par page",
        "page": "Page",
        "of": "sur",
        "records_found": "Enregistrements correspondants",
        "no_records": "Aucun enregistrement ne correspond à ces filtres.",
        "results": "Résultats",
        "details": "Détails de l’enregistrement",
        "choose_record": "Choisir un enregistrement (les doublons sont préservés)",
        "export": "Préparer l’export CSV (toutes les colonnes)",
        "export_ready": "L’export CSV est prêt.",
        "export_too_large": "L’export dépasse la limite de sécurité de 50 Mio. Réduisez les filtres et réessayez.",
        "export_error": "Impossible de préparer le CSV : ",
        "redshift_stats": "Statistiques du redshift",
        "mean": "Moyenne",
        "median": "Médiane",
        "minimum": "Minimum",
        "maximum": "Maximum",
        "missing": "Valeurs manquantes par colonne",
        "missing_note": "Manquant signifie NULL, texte vide ou texte composé d’espaces.",
        "column": "Colonne",
        "missing_count": "Valeurs manquantes",
        "missing_pct": "Manquants (%)",
        "database_info": "Informations sur la base de données",
        "database_file": "Fichier de base de données",
        "table": "Table",
        "records": "Enregistrements",
        "columns": "Colonnes",
        "mode": "Mode d’accès",
        "readonly": "Lecture seule (la base n’est pas modifiée)",
        "about_text": "SPACE OBSERVATORY est une interface d’exploration du catalogue existant de supernovae. Elle lit la base SQLite sans modifier les données scientifiques.",
        "db_missing": "Fichier de base de données introuvable : ",
        "schema_error": "La base ne contient pas la table ou les colonnes nécessaires : ",
        "load_error": "Impossible d’ouvrir la base de données : ",
        "all_records": "Tous les enregistrements du catalogue",
        "record_id": "Identifiant interne de ligne",
        "footer": "Les valeurs scientifiques et les enregistrements sources sont affichés tels qu’ils sont stockés dans la base.",
        "no_redshift": "Aucune valeur numérique valide de redshift n’est disponible.",
        "year_unknown": "Année inconnue",
    },
    "RU": {
        "subtitle": "Исследуйте Вселенную сверхновых",
        "language": "Язык",
        "navigation": "Навигация",
        "dashboard": "Панель управления",
        "catalogue": "Каталог",
        "analysis": "Научный анализ",
        "about": "О проекте",
        "overview": "Окно во Вселенную сверхновых",
        "total": "Записи каталога",
        "types": "Различные заявленные типы",
        "redshifts": "Корректные значения красного смещения",
        "photometry": "Фотометрические измерения",
        "top_types": "Наиболее частые заявленные типы",
        "discoveries": "Открытия по годам",
        "redshift_dist": "Распределение красного смещения (выборка)",
        "search": "Поиск по имени, псевдониму, галактике или типу",
        "search_hint": "Например: SN1990I",
        "type_filter": "Заявленный тип",
        "all_types": "Все типы",
        "redshift_filter": "Включить фильтр максимального красного смещения",
        "max_redshift": "Максимальное красное смещение",
        "rows_per_page": "Строк на странице",
        "page": "Страница",
        "of": "из",
        "records_found": "Найдено записей",
        "no_records": "По заданным фильтрам записи не найдены.",
        "results": "Результаты",
        "details": "Подробности записи",
        "choose_record": "Выберите запись (дубликаты сохраняются)",
        "export": "Подготовить экспорт CSV (все столбцы)",
        "export_ready": "Экспорт CSV готов.",
        "export_too_large": "Экспорт превышает безопасный предел 50 МиБ. Уточните фильтры и повторите попытку.",
        "export_error": "Не удалось подготовить CSV: ",
        "redshift_stats": "Статистика красного смещения",
        "mean": "Среднее",
        "median": "Медиана",
        "minimum": "Минимум",
        "maximum": "Максимум",
        "missing": "Пропущенные значения по столбцам",
        "missing_note": "Пропуск: NULL, пустой текст или текст только из пробелов.",
        "column": "Столбец",
        "missing_count": "Пропущенные значения",
        "missing_pct": "Пропуски (%)",
        "database_info": "Информация о базе данных",
        "database_file": "Файл базы данных",
        "table": "Таблица",
        "records": "Записи",
        "columns": "Столбцы",
        "mode": "Режим доступа",
        "readonly": "Только чтение (база данных не изменяется)",
        "about_text": "SPACE OBSERVATORY — интерфейс для изучения существующего каталога сверхновых. Приложение читает SQLite без изменения научных записей.",
        "db_missing": "Файл базы данных не найден: ",
        "schema_error": "В базе отсутствует необходимая таблица или столбцы: ",
        "load_error": "Не удалось открыть базу данных: ",
        "all_records": "Все записи каталога",
        "record_id": "Внутренний идентификатор строки",
        "footer": "Научные значения и исходные записи отображаются в том виде, в котором они хранятся в базе.",
        "no_redshift": "Корректные числовые значения красного смещения отсутствуют.",
        "year_unknown": "Год неизвестен",
    },
}

# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------
st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp { background: radial-gradient(ellipse at 15% 0%, #14294b 0%, #091426 42%, #050b16 100%); color: #edf3ff; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1c34 0%, #081222 100%); border-right: 1px solid rgba(220,176,83,.25); }
.block-container { padding-top: 1.7rem; padding-bottom: 2rem; max-width: 1500px; }
h1,h2,h3 { color: #e8bd68 !important; letter-spacing: .2px; }
[data-testid="stMetric"] { background: rgba(18,36,64,.78); border: 1px solid rgba(224,183,99,.28); padding: 15px 18px; border-radius: 13px; }
[data-testid="stMetricValue"] { color: #f4d28e !important; }
.stButton > button, .stDownloadButton > button { border: 1px solid #c99d4d; background: linear-gradient(90deg,#b88736,#e2bd70); color: #101827; font-weight: 700; border-radius: 9px; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color: #f4d99c; color: #050b16; }
[data-testid="stDataFrame"] { border: 1px solid rgba(220,176,83,.2); border-radius: 10px; }
hr { border-color: rgba(220,176,83,.25); }
.brand { font-size: 1.45rem; font-weight: 800; letter-spacing: 2px; color: #e8bd68; }
.subbrand { color: #a9bdd9; font-size: .88rem; margin-top: -.35rem; }
.small-note { color: #a9bdd9; font-size: .85rem; }
.author-card {
    margin: 14px 0 18px 0;
    padding: 12px 11px;
    border: 1px solid rgba(232,189,104,.38);
    border-radius: 10px;
    background: rgba(18,36,64,.72);
}
.author-label {
    color: #e8bd68;
    font-size: .66rem;
    font-weight: 800;
    letter-spacing: 1.2px;
    margin-bottom: 7px;
}
.author-name {
    color: #f3f6fc;
    font-size: .78rem;
    line-height: 1.4;
    font-weight: 750;
}
.author-id {
    color: #a9bdd9;
    font-size: .72rem;
    margin-top: 5px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Database access — each connection is explicitly read-only.
# -----------------------------------------------------------------------------
def valid_number(value: Any) -> int:
    if value is None:
        return 0
    value = str(value).strip()
    if not NUMBER_RE.fullmatch(value):
        return 0
    try:
        return int(math.isfinite(float(value)))
    except (ValueError, OverflowError):
        return 0


def get_connection() -> sqlite3.Connection:
    if not DB_FILE.is_file():
        raise FileNotFoundError(str(DB_FILE))
    uri = DB_FILE.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.create_function("is_valid_number", 1, valid_number, deterministic=True)
    return conn

def get_rochester_connection() -> sqlite3.Connection:
    if not ROCHESTER_DB_FILE.is_file():
        raise FileNotFoundError(str(ROCHESTER_DB_FILE))
    uri = ROCHESTER_DB_FILE.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


@st.cache_data(show_spinner=False, ttl=300)
def get_schema_and_counts(db_path: str):
    conn = get_connection()
    try:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)
        ).fetchone()
        if not table_exists:
            raise RuntimeError(f"Table '{TABLE}' not found")
        columns = [r[1] for r in conn.execute(f"PRAGMA table_info({quote_identifier(TABLE)})")]
        required = {"name", "alias", "host", "claimedtype", "redshift", "phot_count", "discoverdate"}
        missing = sorted(required - set(columns))
        if missing:
            raise RuntimeError("Missing required columns: " + ", ".join(missing))
        row = conn.execute(f"SELECT COUNT(*) AS n FROM {quote_identifier(TABLE)}").fetchone()
        return columns, int(row["n"])
    finally:
        conn.close()


def query_df(sql: str, params=()) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def query_one(sql: str, params=()):
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        try:
            return cur.fetchone()
        finally:
            cur.close()
    finally:
        conn.close()


def get_filter_sql(search: str, selected_type: str, use_z: bool, max_z: float):
    clauses, params = [], []
    if search.strip():
        pattern = f"%{search.strip()}%"
        clauses.append("(name LIKE ? COLLATE NOCASE OR alias LIKE ? COLLATE NOCASE OR host LIKE ? COLLATE NOCASE OR claimedtype LIKE ? COLLATE NOCASE)")
        params.extend([pattern] * 4)
    if selected_type != "__ALL__":
        clauses.append("claimedtype = ?")
        params.append(selected_type)
    if use_z:
        clauses.append("is_valid_number(redshift)=1 AND CAST(TRIM(redshift) AS REAL) <= ?")
        params.append(float(max_z))
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params

# -----------------------------------------------------------------------------
# Sidebar / language
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="brand">✦ SPACE OBSERVATORY</div>', unsafe_allow_html=True)
    st.markdown('<div class="subbrand">SUPERNOVA SCIENCE PLATFORM</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="author-card">'
        '<div class="author-label">DEVELOPER / AUTHOR</div>'
        '<div class="author-name">MBEMBA DIABANTSA LOICK JIREL</div>'
        '<div class="author-id">STUDENT ID: B23-105</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    lang = st.selectbox("Language / Langue / Язык", ["EN", "FR", "RU"], index=0, key="language")
    t = TEXT[lang]
    page = st.radio(t["navigation"], [t["dashboard"], t["catalogue"], t["analysis"], t["about"]], key="navigation")

try:
    columns, total_db_rows = get_schema_and_counts(str(DB_FILE))
except FileNotFoundError:
    st.error(t["db_missing"] + str(DB_FILE))
    st.stop()
except Exception as exc:
    st.error(t["schema_error"] + str(exc))
    st.stop()

# Header
st.markdown("# ✦ SPACE OBSERVATORY")
st.markdown(f"**{t['subtitle']}**")
st.caption(t["footer"])
st.divider()

# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
if page == t["dashboard"]:
    st.subheader(t["overview"])
    stats = query_one(f"""SELECT
        COUNT(*) AS total,
        COUNT(DISTINCT NULLIF(TRIM(claimedtype),'')) AS types,
        SUM(CASE WHEN is_valid_number(redshift)=1 THEN 1 ELSE 0 END) AS redshifts,
        SUM(CASE WHEN is_valid_number(phot_count)=1 THEN CAST(TRIM(phot_count) AS REAL) ELSE 0 END) AS photometry
        FROM {quote_identifier(TABLE)}""")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t["total"], f"{int(stats['total'] or 0):,}")
    c2.metric(t["types"], f"{int(stats['types'] or 0):,}")
    c3.metric(t["redshifts"], f"{int(stats['redshifts'] or 0):,}")
    phot = float(stats["photometry"] or 0)
    c4.metric(t["photometry"], f"{phot:,.0f}")

    left, right = st.columns(2)
    with left:
        type_df = query_df(f"""SELECT COALESCE(NULLIF(TRIM(claimedtype),''),'Unknown') AS type,
            COUNT(*) AS records FROM {quote_identifier(TABLE)}
            GROUP BY COALESCE(NULLIF(TRIM(claimedtype),''),'Unknown')
            ORDER BY records DESC LIMIT 18""")
        st.subheader(t["top_types"])
        if not type_df.empty:
            fig = px.bar(type_df.sort_values("records"), x="records", y="type", orientation="h", color="records", color_continuous_scale="Cividis")
            fig.update_layout(template="plotly_dark", height=470, margin=dict(l=10,r=10,t=20,b=10), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
    with right:
        # Main catalogue V2: keep its records separate from Rochester.
        year_v2 = query_df(f"""
            SELECT
                CASE
                    WHEN discoverdate IS NOT NULL
                    AND TRIM(CAST(discoverdate AS TEXT))
                        GLOB '[12][0-9][0-9][0-9]*'
                    THEN SUBSTR(TRIM(CAST(discoverdate AS TEXT)), 1, 4)
                    ELSE ?
                END AS year,
                COUNT(*) AS records
            FROM {quote_identifier(TABLE)}
            GROUP BY year
        """, (t["year_unknown"],))
        year_v2["source"] = "Main catalogue V2"

        # Rochester Astronomy: use actual discovery year, not archive year.
        conn_r = get_rochester_connection()
        try:
            year_rochester = pd.read_sql_query(
                """
                SELECT
                    CAST(discovery_year AS TEXT) AS year,
                    COUNT(*) AS records
                FROM rochester
                WHERE discovery_year BETWEEN 2023 AND 2026
                GROUP BY discovery_year
                ORDER BY discovery_year
                """,
                conn_r,
            )
        finally:
            conn_r.close()

        year_rochester["source"] = "Rochester Astronomy"
        year_df = pd.concat([year_v2, year_rochester], ignore_index=True)
        year_df["year"] = year_df["year"].astype(str)

        year_order = sorted(
            year for year in year_df["year"].unique() if year.isdigit()
        )
        if t["year_unknown"] in year_df["year"].values:
            year_order.append(t["year_unknown"])

        st.subheader(t["discoveries"])
        if not year_df.empty:
            fig = px.line(
                year_df,
                x="year",
                y="records",
                color="source",
                markers=True,
                category_orders={"year": year_order},
                labels={
                    "year": "Year",
                    "records": "Number of records",
                    "source": "Data source",
                },
            )
            fig.update_traces(line=dict(width=3))
            fig.update_layout(
                template="plotly_dark",
                height=470,
                margin=dict(l=10, r=10, t=20, b=10),
                xaxis_title="Year",
                yaxis_title="Number of records",
                legend_title="Data source",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Focused view of recent years: V2 historical records and Rochester records.
    recent_v2 = year_v2[
        year_v2["year"].astype(str).str.fullmatch(r"20(?:1[5-9]|2[0-6])")
    ].copy()
    recent_rochester = year_rochester.copy()
    recent_df = pd.concat([recent_v2, recent_rochester], ignore_index=True)
    recent_df["year"] = recent_df["year"].astype(str)

    st.subheader("Recent discoveries (2015–2026)")
    st.caption(
        "The 2026 count is provisional: the year is still in progress. "
        "Rochester values represent listed records, not exclusively confirmed supernovae."
    )
    if not recent_df.empty:
        recent_order = [str(y) for y in range(2015, 2027)]
        recent_fig = px.line(
            recent_df,
            x="year",
            y="records",
            color="source",
            markers=True,
            category_orders={"year": recent_order},
            labels={
                "year": "Year",
                "records": "Number of records",
                "source": "Data source",
            },
        )
        recent_fig.update_traces(line=dict(width=3))
        recent_fig.update_layout(
            template="plotly_dark",
            height=420,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title="Year",
            yaxis_title="Number of records",
            legend_title="Data source",
            xaxis=dict(type="category", tickangle=0),
        )
        st.plotly_chart(recent_fig, use_container_width=True)

    st.subheader("Redshift Distribution (Logarithmic Scale)")
    st.caption(
        "Histogram of valid redshift measurements from the main catalogue. "
        "The vertical axis uses a base-10 logarithmic scale so that both "
        "frequent and rare bins remain visible. Bins with zero records cannot "
        "be displayed on a logarithmic axis."
    )
    redshift_df = query_df(f"""SELECT CAST(TRIM(redshift) AS REAL) AS redshift
        FROM {quote_identifier(TABLE)} WHERE is_valid_number(redshift)=1
        ORDER BY RANDOM() LIMIT 50000""")
    if not redshift_df.empty:
        fig = px.histogram(
            redshift_df,
            x="redshift",
            nbins=60,
            opacity=0.88,
        )
        fig.update_layout(
            template="plotly_dark",
            height=420,
            margin=dict(l=18, r=18, t=35, b=18),
            title=dict(
                text="Distribution of redshift measurements",
                x=0.02,
                xanchor="left",
            ),
            xaxis_title="Redshift (z)",
            yaxis_title="Number of records — log₁₀ scale",
            bargap=0.06,
            showlegend=False,
        )
        # Base-10 logarithmic frequency axis with readable decade ticks.
        fig.update_yaxes(
            type="log",
            dtick=1,
            tickformat="~s",
            exponentformat="none",
            showgrid=True,
            minor=dict(showgrid=True),
        )
        fig.update_xaxes(showgrid=False, zeroline=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(t["no_redshift"])

# -----------------------------------------------------------------------------
# Catalogue
# -----------------------------------------------------------------------------
elif page == t["catalogue"]:
    st.subheader(t["catalogue"])
    type_rows = query_df(f"SELECT DISTINCT claimedtype FROM {quote_identifier(TABLE)} WHERE claimedtype IS NOT NULL AND TRIM(claimedtype)<>'' ORDER BY claimedtype")
    type_values = [str(x) for x in type_rows["claimedtype"].tolist()]
    with st.container(border=True):
        search = st.text_input(t["search"], placeholder=t["search_hint"], key="catalogue_search")
        f1, f2, f3 = st.columns([1.2, 1, 1])
        with f1:
            type_choice = st.selectbox(t["type_filter"], [t["all_types"]] + type_values, key="type_choice")
            selected_type = "__ALL__" if type_choice == t["all_types"] else type_choice
        with f2:
            use_z = st.checkbox(t["redshift_filter"], value=False, key="use_redshift")
        with f3:
            max_z = st.number_input(t["max_redshift"], min_value=0.0, max_value=20.0, value=1.5, step=0.1, disabled=not use_z, key="max_redshift")
        page_size = st.selectbox(t["rows_per_page"], PAGE_SIZES, index=1, key="page_size")

    where_sql, params = get_filter_sql(search, selected_type, use_z, max_z)
    count_row = query_one(f"SELECT COUNT(*) AS n FROM {quote_identifier(TABLE)}{where_sql}", params)
    filtered_total = int(count_row["n"])
    pages = max(1, math.ceil(filtered_total / page_size))
    if "catalogue_page" not in st.session_state:
        st.session_state.catalogue_page = 1
    st.session_state.catalogue_page = min(max(1, int(st.session_state.catalogue_page)), pages)
    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        if st.button("←", disabled=st.session_state.catalogue_page <= 1, key="prev_page"):
            st.session_state.catalogue_page -= 1
            st.rerun()
    with p2:
        st.markdown(f"<div style='text-align:center;padding-top:8px'>{t['page']} <b>{st.session_state.catalogue_page}</b> {t['of']} {pages} · {t['records_found']}: <b>{filtered_total:,}</b></div>", unsafe_allow_html=True)
    with p3:
        if st.button("→", disabled=st.session_state.catalogue_page >= pages, key="next_page"):
            st.session_state.catalogue_page += 1
            st.rerun()

    offset = (st.session_state.catalogue_page - 1) * page_size
    preview_cols = [c for c in ["name", "claimedtype", "redshift", "discoverdate", "host"] if c in columns]
    select_cols = ", ".join(quote_identifier(c) for c in preview_cols)
    page_df = query_df(f"SELECT rowid AS _rowid_, {select_cols} FROM {quote_identifier(TABLE)}{where_sql} ORDER BY rowid LIMIT ? OFFSET ?", params + [page_size, offset])
    st.subheader(t["results"])
    if page_df.empty:
        st.info(t["no_records"])
    else:
        display_df = page_df.drop(columns=["_rowid_"])
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.subheader(t["details"])
        row_options = page_df["_rowid_"].astype(int).tolist()
        row_labels = {}
        for _, r in page_df.iterrows():
            nm = str(r.get("name", "(unnamed)"))
            typ = str(r.get("claimedtype", ""))
            row_labels[int(r["_rowid_"])] = f"{nm} | {typ} | rowid={int(r['_rowid_'])}"
        selected_rowid = st.selectbox(t["choose_record"], row_options, format_func=lambda x: row_labels[x], key="detail_rowid")
        detail = query_df(f"SELECT rowid AS _rowid_, * FROM {quote_identifier(TABLE)} WHERE rowid=?", (int(selected_rowid),))
        if not detail.empty:
            detail_long = pd.DataFrame({t["column"]: detail.columns, "Value": [str(v) if v is not None else "NULL" for v in detail.iloc[0].tolist()]})
            st.dataframe(detail_long, use_container_width=True, hide_index=True, height=450)

    st.divider()
    if st.button(t["export"], key="prepare_csv", disabled=filtered_total == 0):
        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(prefix="space_observatory_", suffix=".csv")
            import os
            os.close(fd)
            class BoundedTextWriter:
                def __init__(self, handle, limit):
                    self.handle, self.limit, self.written = handle, limit, 0
                def write(self, text):
                    size = len(text.encode("utf-8"))
                    if self.written + size > self.limit:
                        raise OverflowError("CSV exceeds configured size limit")
                    self.written += size
                    return self.handle.write(text)
            conn = get_connection()
            try:
                cursor = conn.execute(f"SELECT * FROM {quote_identifier(TABLE)}{where_sql} ORDER BY rowid", params)
                with open(temp_path, "w", encoding="utf-8-sig", newline="") as handle:
                    writer = BoundedTextWriter(handle, CSV_MAX_BYTES)
                    csv_writer = csv.writer(writer)
                    csv_writer.writerow([d[0] for d in cursor.description])
                    while True:
                        batch = cursor.fetchmany(CSV_BATCH_SIZE)
                        if not batch:
                            break
                        csv_writer.writerows([tuple(row) for row in batch])
                cursor.close()
            finally:
                conn.close()
            with open(temp_path, "rb") as f:
                csv_bytes = f.read(CSV_MAX_BYTES + 1)
            if len(csv_bytes) > CSV_MAX_BYTES:
                raise OverflowError("CSV exceeds configured size limit")
            st.session_state["csv_export_bytes"] = csv_bytes
            st.session_state["csv_export_name"] = "space_observatory_filtered.csv"
            st.success(t["export_ready"])
        except OverflowError:
            st.session_state.pop("csv_export_bytes", None)
            st.error(t["export_too_large"])
        except Exception as exc:
            st.session_state.pop("csv_export_bytes", None)
            st.error(t["export_error"] + str(exc))
        finally:
            if temp_path:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except OSError:
                    pass
    if st.session_state.get("csv_export_bytes"):
        st.download_button(
            label="⬇ Download CSV" if lang == "EN" else ("⬇ Télécharger le CSV" if lang == "FR" else "⬇ Скачать CSV"),
            data=st.session_state["csv_export_bytes"],
            file_name=st.session_state.get("csv_export_name", "space_observatory_filtered.csv"),
            mime="text/csv",
            key="download_csv",
        )
        st.caption("CSV is generated in batches and capped at 50 MiB; the final download is held in app memory.")

# -----------------------------------------------------------------------------
# Scientific analysis
# -----------------------------------------------------------------------------
elif page == t["analysis"]:
    st.subheader(t["redshift_stats"])
    z_df = query_df(f"SELECT CAST(TRIM(redshift) AS REAL) AS z FROM {quote_identifier(TABLE)} WHERE is_valid_number(redshift)=1 ORDER BY CAST(TRIM(redshift) AS REAL)")
    if not z_df.empty:
        values = z_df["z"].astype(float)
        med = float(values.median())
        a, b, c, d = st.columns(4)
        a.metric(t["mean"], f"{values.mean():.6g}")
        b.metric(t["median"], f"{med:.6g}")
        c.metric(t["minimum"], f"{values.min():.6g}")
        d.metric(t["maximum"], f"{values.max():.6g}")
    else:
        st.info(t["no_redshift"])

    st.subheader(t["missing"])
    st.caption(t["missing_note"])
    # One SQL query computes missing counts for every catalogue column.
    expressions = []
    for col in columns:
        qcol = quote_identifier(col)
        expressions.append(f"SUM(CASE WHEN {qcol} IS NULL OR TRIM(CAST({qcol} AS TEXT))='' THEN 1 ELSE 0 END) AS {qcol}")
    missing_row = query_one(f"SELECT {', '.join(expressions)} FROM {quote_identifier(TABLE)}")
    missing_data = []
    for col in columns:
        count = int(missing_row[col] or 0)
        missing_data.append({t["column"]: col, t["missing_count"]: count, t["missing_pct"]: round(100 * count / total_db_rows, 2) if total_db_rows else 0.0})
    missing_df = pd.DataFrame(missing_data).sort_values(t["missing_count"], ascending=False)
    st.dataframe(missing_df, use_container_width=True, hide_index=True, height=520)

# -----------------------------------------------------------------------------
# About
# -----------------------------------------------------------------------------
else:
    st.subheader(t["about"])
    st.write(t["about_text"])
    st.subheader(t["database_info"])
    info = [
        (t["database_file"], str(DB_FILE)),
        (t["table"], TABLE),
        (t["records"], f"{total_db_rows:,}"),
        (t["columns"], f"{len(columns)}"),
        (t["mode"], t["readonly"]),
    ]
    st.table(pd.DataFrame(info, columns=[t["column"], "Value"]))

st.divider()
st.markdown(
    f"<div class='small-note'>✦ SPACE OBSERVATORY · {t['footer']}<br>"
    "<strong>Author:</strong> MBEMBA DIABANTSA LOICK JIREL · "
    "<strong>Student ID:</strong> B23-105</div>",
    unsafe_allow_html=True,
)
