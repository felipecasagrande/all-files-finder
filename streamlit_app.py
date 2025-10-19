import io
from datetime import datetime, date
from typing import List, Optional

import pandas as pd
import streamlit as st

# =============================================================================
# CONFIGURAÇÕES GERAIS
# =============================================================================
st.set_page_config(page_title="All Files Finder - Felipe", page_icon="🔎", layout="wide")
st.title("All Files Finder - Felipe")
st.caption("Faça upload de arquivos CSV/XLSX e filtre seus registros por nome, extensão, data, tamanho, pasta e mais.")

# =============================================================================
# FUNÇÕES DE LEITURA
# =============================================================================
@st.cache_data(show_spinner=False)
def read_csv_smart(file) -> pd.DataFrame:
    """Tenta diferentes encodings e separadores para CSVs"""
    for enc in ["utf-8", "latin1", "utf-16"]:
        for sep in [",", ";", "|", "\t"]:
            try:
                file.seek(0)
                df = pd.read_csv(file, encoding=enc, sep=sep)
                if df.shape[1] > 1:
                    return df
            except Exception:
                continue
    raise ValueError("❌ Não foi possível ler o arquivo CSV. Verifique o formato.")

@st.cache_data(show_spinner=False)
def read_excel_smart(file) -> pd.DataFrame:
    return pd.read_excel(file, engine="openpyxl")

# =============================================================================
# NORMALIZAÇÃO DE DADOS
# =============================================================================
@st.cache_data(show_spinner=False)
def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa colunas, tenta converter tipos sem exagerar"""
    df = df.rename(columns={c: c.strip() for c in df.columns})

    # Converter somente colunas com nome de data
    for c in df.columns:
        cname = c.lower()
        if any(k in cname for k in ["data", "date", "dia"]):
            try:
                df[c] = pd.to_datetime(df[c], errors="coerce")
            except Exception:
                pass
        # Converter apenas se a coluna for majoritariamente numérica
        elif df[c].dtype == "object":
            s = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False), errors="coerce")
            if s.notna().mean() >= 0.8:
                df[c] = s
    return df

# =============================================================================
# DETECTAR COLUNA DE NOME DE ARQUIVO
# =============================================================================
def detect_filename_column(cols: List[str]) -> Optional[str]:
    keys = ["file", "arquivo", "name", "nome", "filename", "path", "caminho"]
    for k in keys:
        for c in cols:
            if k in c.lower():
                return c
    return cols[0] if cols else None

# =============================================================================
# FILTROS LATERAIS
# =============================================================================
def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔎 Filtros")
    st.sidebar.caption("Aplique filtros para refinar os resultados.")
    filtered = df.copy()

    # Coluna principal
    file_col_guess = detect_filename_column(list(df.columns))
    file_col = st.sidebar.selectbox(
        "Coluna de busca principal (nome/arquivo)",
        options=list(df.columns),
        index=(list(df.columns).index(file_col_guess) if file_col_guess in df.columns else 0)
    )

    # Busca textual
    quick_search = st.sidebar.text_input("Busca por texto (contém)", placeholder="Ex.: relatorio, contrato, .xlsx ...")
    if quick_search:
        mask = filtered[file_col].astype(str).str.contains(quick_search, case=False, na=False, regex=True)
        filtered = filtered[mask]

    # Filtros avançados
    with st.sidebar.expander("Filtros avançados", expanded=False):
        for c in filtered.columns:
            s = filtered[c]

            if pd.api.types.is_numeric_dtype(s):
                min_v, max_v = s.min(skipna=True), s.max(skipna=True)
                if pd.notna(min_v) and pd.notna(max_v) and min_v != max_v:
                    r = st.slider(f"{c} (intervalo)", float(min_v), float(max_v), (float(min_v), float(max_v)))
                    filtered = filtered[(s >= r[0]) & (s <= r[1])]
            elif pd.api.types.is_datetime64_any_dtype(s):
                min_d, max_d = pd.to_datetime(s.min(skipna=True)), pd.to_datetime(s.max(skipna=True))
                if pd.notna(min_d) and pd.notna(max_d) and min_d != max_d:
                    dr = st.date_input(f"{c} (período)", value=(min_d.date(), max_d.date()))
                    if isinstance(dr, tuple) and len(dr) == 2:
                        start_d, end_d = dr
                        mask = (pd.to_datetime(s) >= pd.Timestamp(start_d)) & (pd.to_datetime(s) <= pd.Timestamp(end_d))
                        filtered = filtered[mask]
            else:
                if s.nunique(dropna=True) > 1 and s.nunique(dropna=True) <= 100:
                    opts = sorted([x for x in s.dropna().unique().tolist() if str(x).strip() != ""])
                    picked = st.multiselect(f"{c} (seleção múltipla)", options=opts)
                    if picked:
                        filtered = filtered[filtered[c].isin(picked)]

    return filtered

# =============================================================================
# KPIs SUPERIORES
# =============================================================================
def kpi_header(df: pd.DataFrame, filtered: pd.DataFrame):
    total, sel = len(df), len(filtered)
    cols = st.columns(4)
    cols[0].metric("Registros filtrados", f"{sel:,}".replace(",", "."), delta=f"de {total:,}".replace(",", "."))

    file_col_guess = detect_filename_column(list(df.columns))
    if file_col_guess and file_col_guess in df.columns:
        cols[1].metric("Itens únicos", f"{df[file_col_guess].nunique():,}".replace(",", "."))

    # Tamanho total (se existir)
    size_cols = [c for c in df.columns if "size" in c.lower() or "bytes" in c.lower()]
    if size_cols:
        try:
            total_bytes = pd.to_numeric(filtered[size_cols[0]], errors="coerce").sum()
            def fmt_bytes(n):
                for unit in ["B", "KB", "MB", "GB", "TB"]:
                    if n < 1024:
                        return f"{n:.1f} {unit}"
                    n /= 1024
                return f"{n:.1f} PB"
            cols[2].metric("Tamanho total", fmt_bytes(total_bytes))
        except Exception:
            pass

    # Extensões
    ext_cols = [c for c in df.columns if "ext" in c.lower() or "tipo" in c.lower()]
    if ext_cols:
        cols[3].metric("Extensões únicas", f"{filtered[ext_cols[0]].nunique():,}".replace(",", "."))

# =============================================================================
# APP PRINCIPAL
# =============================================================================
def main():
    with st.sidebar:
        st.subheader("📤 Upload de arquivos")
        uploads = st.file_uploader("Envie um ou mais arquivos (.csv ou .xlsx)", type=["csv", "xlsx"], accept_multiple_files=True)
        st.markdown("---")
        st.caption("Você pode juntar várias planilhas em uma visão única.")

    if not uploads:
        st.info("Envie ao menos um arquivo CSV/XLSX para começar.")
        st.stop()

    frames = []
    for f in uploads:
        if f.name.lower().endswith(".csv"):
            df = read_csv_smart(f)
        else:
            df = read_excel_smart(f)
        df["__source_file"] = f.name
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df = normalize_dataframe(df)

    filtered = sidebar_filters(df)
    kpi_header(df, filtered)

    st.markdown("### 📋 Tabela de resultados")
    st.dataframe(filtered, use_container_width=True, height=520)

    st.markdown("#### ⬇️ Exportar resultados")
    csv_data = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Baixar CSV filtrado", data=csv_data, file_name="all_files_finder_filtrado.csv", mime="text/csv")

    # Gráfico por extensão
    ext_col = next((c for c in filtered.columns if "ext" in c.lower() or "tipo" in c.lower()), None)
    if ext_col:
        st.markdown("### 📊 Quantidade por extensão/tipo")
        chart_df = filtered[ext_col].value_counts(dropna=False).reset_index()
        chart_df.columns = [ext_col, "quantidade"]
        st.bar_chart(chart_df.set_index(ext_col)["quantidade"])

    st.markdown("---")
    st.caption("Desenvolvido com ❤️ em Streamlit · All Files Finder - Felipe")

# =============================================================================
# EXECUÇÃO
# =============================================================================
if __name__ == "__main__":
    main()
