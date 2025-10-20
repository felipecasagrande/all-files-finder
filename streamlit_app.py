import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
import io, json, os, urllib.parse

# ======================================================
# ⚙️ CONFIGURAÇÕES
# ======================================================
st.set_page_config(page_title="All Files Finder - Felipe", layout="wide")
st.title("📂 All Files Finder - Felipe")
st.write("Leitura e filtragem de planilhas CSV/XLSX diretamente do Google Drive com integração segura.")

# ======================================================
# 💅 ESTILO VISUAL
# ======================================================
st.markdown("""
<style>
div[data-baseweb="input"] > div {
    border: 2px solid #00ffff !important;
    box-shadow: 0 0 10px rgba(0,255,255,0.3);
    border-radius: 8px !important;
}
table a {color:#00ffff;text-decoration:none;}
button.copy-btn {
    background-color:#003333;
    color:#00ffff;
    border:none;
    border-radius:6px;
    padding:4px 8px;
    cursor:pointer;
}
button.copy-btn:hover {background-color:#004d4d;}
</style>
""", unsafe_allow_html=True)

# ======================================================
# 🔐 GOOGLE DRIVE
# ======================================================
try:
    creds_json = st.secrets["GCP_SA_KEY"]
    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_dict)
    service = build("drive", "v3", credentials=creds)
    FOLDER_ID = "15ToUbVb9fKNDFECffoHWGr3R22_sj4Fy"
except Exception as e:
    st.error(f"Erro ao conectar com o Google Drive: {e}")
    st.stop()

# ======================================================
# 📂 LISTAR ARQUIVOS DISPONÍVEIS
# ======================================================
results = service.files().list(
    q=f"'{FOLDER_ID}' in parents and (mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='text/csv')",
    fields="files(id, name, mimeType, size)"
).execute()

files = results.get("files", [])
if not files:
    st.warning("Nenhum arquivo CSV/XLSX encontrado.")
    st.stop()

file_options = {f["name"]: f for f in files}
selected_file = st.selectbox("📄 Selecione um arquivo:", list(file_options.keys()))
file_id = file_options[selected_file]["id"]
mime_type = file_options[selected_file]["mimeType"]

# ======================================================
# 📑 LEITURA DIRETA (SEM CHUNKS)
# ======================================================
st.info(f"📥 Carregando **{selected_file}**, aguarde...")

request = service.files().get_media(fileId=file_id)
file_bytes = io.BytesIO(request.execute())

if mime_type == "text/csv" or selected_file.lower().endswith(".csv"):
    df = pd.read_csv(file_bytes, encoding="utf-8", sep=",", engine="python")
else:
    df = pd.read_excel(file_bytes)

st.success(f"✅ Arquivo carregado com {df.shape[0]:,} linhas e {df.shape[1]} colunas.")

# ======================================================
# 🧩 CRIAR COLUNA "TIPO" E FILTRAR EXTENSÕES
# ======================================================
tipos_validos = [".xlsx", ".csv", ".xls", ".py", ".ipynb", ".pbix", ".json", ".xml", ".pdf", ".docx"]

if "Nome" not in df.columns:
    st.error("⚠️ A planilha precisa ter uma coluna chamada 'Nome'.")
    st.dataframe(df.head(20))
    st.stop()

df["Tipo"] = df["Nome"].apply(lambda x: os.path.splitext(str(x))[1].lower().strip())
df = df[df["Tipo"].isin(tipos_validos)].reset_index(drop=True)

st.success(f"🔍 {len(df):,} arquivos mantidos ({len(tipos_validos)} tipos permitidos).")

# ======================================================
# 🎯 FILTRO INTERATIVO
# ======================================================
st.subheader("🎯 Filtros interativos")
col1, col2 = st.columns(2)
with col1:
    coluna_filtro = st.selectbox("Coluna para filtrar", df.columns)
with col2:
    valor_filtro = st.text_input("Valor (parte ou completo)")

if valor_filtro:
    mask = df[coluna_filtro].astype(str).str.contains(valor_filtro, case=False, na=False)
    filtered = df[mask]
else:
    filtered = df

st.markdown(f"**{len(filtered):,} registros filtrados.**")

# ======================================================
# 📊 CONTAGEM POR TIPO DE ARQUIVO
# ======================================================
st.subheader("📁 Tipos de arquivo válidos")
tipo_count = df["Tipo"].value_counts().reset_index()
tipo_count.columns = ["Tipo", "Quantidade"]

col1, col2 = st.columns([1, 2])
with col1:
    st.dataframe(tipo_count, width="stretch")
with col2:
    st.bar_chart(tipo_count.set_index("Tipo"))

# ======================================================
# 📊 CONTAGEM POR PASTA
# ======================================================
st.subheader("📂 Contagem por pasta/local")
if "Local" in df.columns:
    pasta_count = df["Local"].value_counts().reset_index()
    pasta_count.columns = ["Pasta", "Arquivos"]
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(pasta_count.head(20), width="stretch")
    with col2:
        st.bar_chart(pasta_count.head(20).set_index("Pasta"))
else:
    st.warning("Coluna 'Local' não encontrada.")

# ======================================================
# 🧭 FORMATAÇÃO DE DATA
# ======================================================
if "Modificado em" in df.columns:
    df["Modificado em"] = pd.to_datetime(df["Modificado em"], errors="coerce").dt.strftime("%d/%m/%Y")

# ======================================================
# 📥 DOWNLOAD
# ======================================================
csv_data = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Baixar CSV filtrado",
    data=csv_data,
    file_name="all_files_finder_filtrado.csv",
    mime="text/csv"
)

st.markdown("---")
st.caption("Desenvolvido com 💚 em Streamlit · All Files Finder - Felipe")
