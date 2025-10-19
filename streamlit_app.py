
import io
from datetime import datetime, date
from typing import List, Optional, Dict

import pandas as pd
import streamlit as st

st.set_page_config(page_title="All Files Finder - Felipe", page_icon="🔎", layout="wide")

TITLE = "All Files Finder - Felipe"
st.title(TITLE)
st.caption("Faça upload de arquivo(s) CSV/XLSX e filtre seus registros por nome, extensão, datas, tamanho, pasta e mais.")

@st.cache_data(show_spinner=False)
def read_csv_smart(file) -> pd.DataFrame:
    # tenta UTF-8 depois Latin-1
    try:
        return pd.read_csv(file)
    except UnicodeDecodeError:
        file.seek(0)
        return pd.read_csv(file, encoding="latin-1")
    except Exception as e:
        raise e

@st.cache_data(show_spinner=False)
def read_excel_smart(file) -> pd.DataFrame:
    return pd.read_excel(file, engine="openpyxl")

@st.cache_data(show_spinner=False)
def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Normaliza nomes de colunas (sem alterar o original visual)
    renamed = {}
    for c in df.columns:
        renamed[c] = c.strip()
    df = df.rename(columns=renamed)

    # Tenta converter colunas de data e numéricas comuns
    for c in df.columns:
        if df[c].dtype == "object":
            # tenta datetime
            try:
                parsed = pd.to_datetime(df[c], errors="raise", utc=False, dayfirst=False, format=None)
                # aceita apenas se pelo menos 60% virar datetime
                mask = pd.to_datetime(df[c], errors="coerce").notna()
                if mask.mean() >= 0.6:
                    df[c] = pd.to_datetime(df[c], errors="coerce")
            except Exception:
                pass
            # tenta numerificar (sem converter coisas com muitas letras)
            # cuidado: isso pode alterar IDs com zeros à esquerda -> apenas se >=80% numérico
            s = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False), errors="coerce")
            if s.notna().mean() >= 0.8:
                df[c] = s

    return df

def detect_filename_column(cols: List[str]) -> Optional[str]:
    # heurística simples para identificar a coluna que representa o "nome do arquivo"
    keys = ["file", "arquivo", "name", "nome", "filename", "fname", "document", "doc", "path", "caminho"]
    for k in keys:
        for c in cols:
            if k in c.lower():
                return c
    # fallback: se houver poucas colunas texto, pegue a primeira object com muitos valores únicos
    return None

def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔎 Filtros")
    st.sidebar.caption("Aplique filtros para refinar os resultados.")

    filtered = df.copy()

    # Coluna principal de busca (nome do arquivo)
    file_col_guess = detect_filename_column(list(df.columns))
    file_col = st.sidebar.selectbox(
        "Coluna de busca principal (nome/arquivo)",
        options=list(df.columns),
        index=(list(df.columns).index(file_col_guess) if file_col_guess in df.columns else 0),
        help="Selecione a coluna que representa o nome ou caminho do arquivo para busca rápida."
    )

    quick_search = st.sidebar.text_input("Busca por texto (contém)", placeholder="Ex.: relatorio, contrato, .xlsx, .pdf ...")
    if quick_search:
        mask = filtered[file_col].astype(str).str.contains(quick_search, case=False, na=False, regex=True)
        filtered = filtered[mask]

    # Filtros dinâmicos por tipo de coluna
    with st.sidebar.expander("Filtros avançados por coluna", expanded=False):
        for c in filtered.columns:
            s = filtered[c]

            # pular a coluna principal já filtrada acima (mas ainda permitir filtros adicionais se o usuário quiser)
            # aqui optamos por permitir também nos avançados, então não pulamos

            if pd.api.types.is_numeric_dtype(s):
                # Range de números
                min_v, max_v = float(pd.to_numeric(s, errors="coerce").min(skipna=True) or 0), float(pd.to_numeric(s, errors="coerce").max(skipna=True) or 0)
                if pd.notna(min_v) and pd.notna(max_v) and min_v != max_v:
                    r = st.slider(f"{c} (intervalo)", min_value=min_v, max_value=max_v, value=(min_v, max_v))
                    filtered = filtered[(pd.to_numeric(filtered[c], errors="coerce") >= r[0]) & (pd.to_numeric(filtered[c], errors="coerce") <= r[1])]
            elif pd.api.types.is_datetime64_any_dtype(s):
                # Intervalo de datas
                min_d = pd.to_datetime(s.min(skipna=True))
                max_d = pd.to_datetime(s.max(skipna=True))
                if pd.notna(min_d) and pd.notna(max_d) and min_d != max_d:
                    dr = st.date_input(f"{c} (período)", value=(min_d.date(), max_d.date()))
                    if isinstance(dr, tuple) and len(dr) == 2:
                        start_d, end_d = dr
                        mask = (pd.to_datetime(filtered[c]) >= pd.Timestamp(start_d)) & (pd.to_datetime(filtered[c]) <= pd.Timestamp(end_d) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1))
                        filtered = filtered[mask]
            else:
                # Categóricos com poucos valores: multiselect
                nunique = s.nunique(dropna=True)
                if nunique > 1 and nunique <= 150:
                    opts = sorted([x for x in s.dropna().unique().tolist() if str(x).strip() != ""])
                    picked = st.multiselect(f"{c} (seleção múltipla)", options=opts)
                    if picked:
                        filtered = filtered[filtered[c].isin(picked)]

    return filtered

def kpi_header(df: pd.DataFrame, filtered: pd.DataFrame):
    total = len(df)
    sel = len(filtered)

    cols = st.columns(4)
    cols[0].metric("Registros (filtrados)", f"{sel:,}".replace(",", "."), delta=f"de {total:,}".replace(",", "."))

    # Arquivos únicos se existir coluna principal detectada
    file_col_guess = detect_filename_column(list(df.columns))
    if file_col_guess and file_col_guess in df.columns:
        cols[1].metric("Itens únicos", f"{df[file_col_guess].nunique():,}".replace(",", "."))

    # Soma de tamanho se existir
    size_cols = [c for c in df.columns if "size" in c.lower() or "bytes" in c.lower()]
    if size_cols:
        sc = size_cols[0]
        try:
            total_bytes = pd.to_numeric(filtered[sc], errors="coerce").sum()
            def humanize_bytes(n):
                if pd.isna(n):
                    return "-"
                for unit in ["B","KB","MB","GB","TB"]:
                    if n < 1024.0:
                        return f"{n:3.1f} {unit}"
                    n /= 1024.0
                return f"{n:.1f} PB"
            cols[2].metric("Tamanho total (filtrado)", humanize_bytes(total_bytes))
        except Exception:
            pass

    # Se houver coluna de extensão
    ext_cols = [c for c in df.columns if "ext" in c.lower() or "tipo" in c.lower()]
    if ext_cols:
        cols[3].metric("Extensões únicas", f"{filtered[ext_cols[0]].nunique():,}".replace(",", "."))

def main():
    with st.sidebar:
        st.subheader("📤 Upload de arquivos")
        uploads = st.file_uploader("Envie um ou mais arquivos (.csv ou .xlsx)", type=["csv","xlsx"], accept_multiple_files=True)

        st.markdown("---")
        st.caption("Dica: Você pode juntar várias planilhas em uma visão única.")

    if not uploads:
        st.info("Envie ao menos um arquivo CSV/XLSX para começar.")
        st.stop()

    # Ler e concatenar
    frames = []
    for f in uploads:
        if f.name.lower().endswith(".csv"):
            df = read_csv_smart(f)
        else:
            df = read_excel_smart(f)
        df["__source_file"] = f.name  # rastreabilidade
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)

    # Normaliza tipos
    df = normalize_dataframe(df)

    # Filtros
    filtered = sidebar_filters(df)

    # KPIs
    kpi_header(df, filtered)

    st.markdown("### 📋 Tabela de resultados")
    st.caption("Dica: Clique no cabeçalho para ordenar. Use a barra de rolagem para ver todas as colunas.")
    st.dataframe(filtered, use_container_width=True, height=520)

    # Downloads
    st.markdown("#### ⬇️ Exportar resultados")
    csv_data = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Baixar CSV filtrado", data=csv_data, file_name="all_files_finder_filtrado.csv", mime="text/csv")

    # Gráfico opcional por extensão (se existir coluna de extensão)
    ext_col = None
    for c in filtered.columns:
        lc = c.lower()
        if "ext" in lc or lc.endswith("extensão") or "tipo" in lc:
            ext_col = c
            break
    if ext_col:
        st.markdown("### 📊 Quantidade por extensão/tipo")
        chart_df = filtered[ext_col].value_counts(dropna=False).reset_index()
        chart_df.columns = [ext_col, "quantidade"]
        st.bar_chart(chart_df.set_index(ext_col)["quantidade"])

    st.markdown("---")
    st.caption("Desenvolvido com ❤️ em Streamlit · All Files Finder - Felipe")

if __name__ == "__main__":
    main()
