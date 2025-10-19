import streamlit as st
import pandas as pd
from io import BytesIO

# ======================================================
# 🧭 CONFIGURAÇÕES INICIAIS
# ======================================================
st.set_page_config(page_title="All Files Finder - Felipe", layout="wide")
st.title("📂 All Files Finder - Felipe")
st.write("Faça upload de um arquivo **CSV** ou **XLSX** contendo a lista de arquivos para filtrar e explorar seus dados diretamente na nuvem.")

# ======================================================
# 📤 UPLOAD DE ARQUIVO
# ======================================================
uploaded_file = st.file_uploader("Selecione um arquivo CSV ou Excel", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Leitura do arquivo (CSV ou Excel)
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, encoding="utf-8", sep=None, engine="python")
        else:
            df = pd.read_excel(uploaded_file)

        st.success(f"✅ Arquivo carregado: **{uploaded_file.name}**")
        st.write("Dimensões:", df.shape)

        # Exibe os dados em tabela
        st.dataframe(df.head(100), use_container_width=True)

        # ======================================================
        # 🔍 FILTROS INTERATIVOS
        # ======================================================
        st.subheader("🎯 Filtros")

        colunas = df.columns.tolist()
        col1, col2 = st.columns(2)

        with col1:
            coluna_filtro = st.selectbox("Coluna para filtrar", colunas)
        with col2:
            valor_filtro = st.text_input("Valor (parte ou completo)")

        if valor_filtro:
            mask = df[coluna_filtro].astype(str).str.contains(valor_filtro, case=False, na=False)
            filtered = df[mask]
        else:
            filtered = df.copy()

        st.markdown(f"**{len(filtered)} registros filtrados.**")
        st.dataframe(filtered, use_container_width=True)

        # ======================================================
        # 📥 DOWNLOAD DO RESULTADO
        # ======================================================
        csv_data = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Baixar CSV filtrado",
            data=csv_data,
            file_name="all_files_finder_filtrado.csv",
            mime="text/csv"
        )

        # ======================================================
        # 📊 GRÁFICO POR EXTENSÃO / TIPO
        # ======================================================
        ext_col = next((c for c in filtered.columns if "ext" in c.lower() or "tipo" in c.lower()), None)

        if ext_col:
            st.markdown("### 📈 Quantidade por extensão/tipo")
            chart_df = filtered[ext_col].value_counts(dropna=False).reset_index()
            chart_df.columns = [ext_col, "quantidade"]
            st.bar_chart(chart_df.set_index(ext_col)["quantidade"])

        st.markdown("---")
        st.caption("Desenvolvido com ❤️ em Streamlit · All Files Finder - Felipe")

    except Exception as e:
        st.error(f"⚠️ Erro ao processar o arquivo: {e}")
else:
    st.info("Carregue um arquivo para começar.")

# ======================================================
# 🔧 EXECUÇÃO DIRETA (modo seguro)
# ======================================================
if __name__ == "__main__":
    pass
