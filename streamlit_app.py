import streamlit as st
import pandas as pd
import io
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ======================================================
# 🧭 CONFIGURAÇÕES INICIAIS
# ======================================================
st.set_page_config(page_title="All Files Finder - Felipe", layout="wide")
st.title("📂 All Files Finder - Felipe")
st.write("Leitura automática de planilhas **XLSX** diretamente da pasta do Google Drive (conectada com credencial segura).")

# ======================================================
# 🔐 CREDENCIAIS GOOGLE DRIVE (via Streamlit Secrets)
# ======================================================
try:
    sa_json = st.secrets["GCP_SA_KEY"]  # Credenciais seguras
    sa_info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )

    # Inicializa serviço do Google Drive
    drive_service = build("drive", "v3", credentials=creds)
except Exception as e:
    st.error(f"⚠️ Erro ao carregar credenciais do Google Drive: {e}")
    st.stop()

# ======================================================
# 📁 ID DA PASTA DO GOOGLE DRIVE
# ======================================================
FOLDER_ID = "15ToUbVb9fKNDFECffoHWGr3R22_sj4Fy"

# ======================================================
# 📄 LISTA DE ARQUIVOS DISPONÍVEIS NO DRIVE
# ======================================================
try:
    results = drive_service.files().list(
        q=f"'{FOLDER_ID}' in parents and (mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='application/vnd.ms-excel') and trashed=false",
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc"
    ).execute()

    files = results.get("files", [])
except Exception as e:
    st.error(f"❌ Erro ao acessar pasta do Google Drive: {e}")
    st.stop()

if not files:
    st.warning("⚠️ Nenhum arquivo Excel encontrado na pasta do Google Drive.")
    st.stop()

file_names = [f"{f['name']} (modificado em {f['modifiedTime'][:10]})" for f in files]
selected_file = st.selectbox("📄 Selecione um arquivo da pasta do Google Drive:", file_names)

file_id = files[file_names.index(selected_file)]["id"]

# ======================================================
# 📥 DOWNLOAD E LEITURA DO ARQUIVO SELECIONADO
# ======================================================
st.info(f"📂 Carregando arquivo **{files[file_names.index(selected_file)]['name']}**...")
file_content = drive_service.files().get_media(fileId=file_id).execute()
file_bytes = io.BytesIO(file_content)
df = pd.read_excel(file_bytes)

st.success(f"✅ Arquivo carregado: **{files[file_names.index(selected_file)]['name']}**")
st.write("Dimensões:", df.shape)

# ======================================================
# 📊 EXIBIÇÃO E FILTROS INTERATIVOS
# ======================================================
st.dataframe(df.head(100), use_container_width=True)
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
# 📈 GRÁFICO POR EXTENSÃO / TIPO
# ======================================================
ext_col = next((c for c in filtered.columns if "ext" in c.lower() or "tipo" in c.lower()), None)
if ext_col:
    st.markdown("### 📊 Quantidade por extensão/tipo")
    chart_df = filtered[ext_col].value_counts(dropna=False).reset_index()
    chart_df.columns = [ext_col, "quantidade"]
    st.bar_chart(chart_df.set_index(ext_col)["quantidade"])

st.markdown("---")
st.caption("Desenvolvido com ❤️ em Streamlit · All Files Finder - Felipe")

# ======================================================
# 🔧 EXECUÇÃO DIRETA (modo seguro)
# ======================================================
if __name__ == "__main__":
    pass
