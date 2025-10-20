import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
import io, json, urllib.parse, socket

# ======================================================
# 🧭 CONFIGURAÇÕES INICIAIS
# ======================================================
st.set_page_config(page_title="All Files Finder - Felipe", layout="wide")
st.title("📂 All Files Finder - Felipe")
st.write("Leitura automática de planilhas **XLSX** e **CSV** diretamente da pasta do Google Drive (conectada com credencial segura).")

# ======================================================
# 💅 ESTILO PERSONALIZADO
# ======================================================
st.markdown("""
<style>
div[data-baseweb="input"] > div {
    border: 2px solid #00ffff !important;
    box-shadow: 0 0 10px rgba(0,255,255,0.3);
    border-radius: 8px !important;
    transition: border 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
}
div[data-baseweb="input"] > div:focus-within {
    border: 2px solid #00e0e0 !important;
    box-shadow: 0 0 14px rgba(0,255,255,0.6);
}
input:disabled {opacity:1 !important;color:#fff !important;}
div[data-baseweb="input"] input {color:#e8ffff !important;font-weight:500;}
div[data-baseweb="input"] input::placeholder {color:#aefcff !important;opacity:0.7;}
table a {color:#00ffff;text-decoration:none;}
table a:hover {text-decoration:underline;color:#00e0e0;}
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
# ⚙️ DETECTAR AMBIENTE LOCAL OU NUVEM
# ======================================================
def is_running_locally():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip.startswith(("127.", "192.168", "10."))
    except:
        return False

LOCAL_MODE = is_running_locally()

# ======================================================
# 🔐 CONEXÃO GOOGLE DRIVE
# ======================================================
try:
    creds_json = st.secrets["GCP_SA_KEY"]
    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_dict)
    service = build("drive", "v3", credentials=creds)
    FOLDER_ID = "15ToUbVb9fKNDFECffoHWGr3R22_sj4Fy"
except Exception as e:
    st.error(f"⚠️ Erro ao carregar credenciais: {e}")
    st.stop()

# ======================================================
# 📁 LISTAR ARQUIVOS NA PASTA
# ======================================================
results = service.files().list(
    q=f"'{FOLDER_ID}' in parents and (mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='text/csv')",
    fields="files(id, name, mimeType, size)"
).execute()

files = results.get("files", [])
if not files:
    st.warning("⚠️ Nenhum arquivo Excel ou CSV encontrado na pasta do Google Drive.")
    st.stop()

file_options = {f["name"]: f for f in files}
selected_file = st.selectbox("📄 Selecione um arquivo:", list(file_options.keys()))

file_id = file_options[selected_file]["id"]
mime_type = file_options[selected_file]["mimeType"]

# ======================================================
# 📑 LEITURA DO ARQUIVO
# ======================================================
with st.spinner("📥 Carregando dados, aguarde..."):
    request = service.files().get_media(fileId=file_id)
    file_data = io.BytesIO(request.execute())

    if mime_type == "text/csv" or selected_file.lower().endswith(".csv"):
        df = pd.read_csv(file_data, encoding="utf-8", sep=None, engine="python")
    else:
        df = pd.read_excel(file_data)

# Limitar linhas grandes
MAX_ROWS = 50000
if len(df) > MAX_ROWS:
    st.warning(f"⚠️ Arquivo grande ({len(df):,} linhas). Exibindo apenas as primeiras {MAX_ROWS:,} linhas.")
    df = df.head(MAX_ROWS)

st.success(f"✅ Arquivo carregado com {df.shape[0]} linhas e {df.shape[1]} colunas.")
st.dataframe(df.head(50), width="stretch")

# ======================================================
# 🎯 FILTROS INTERATIVOS
# ======================================================
st.subheader("🎯 Filtros interativos")
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

# ======================================================
# 🧭 LINKS E DATAS FORMATADAS
# ======================================================
df_view = filtered.copy()
col_nome = next((c for c in df_view.columns if "nome" in c.lower()), None)
col_local = next((c for c in df_view.columns if "local" in c.lower()), None)
col_data = next((c for c in df_view.columns if "modific" in c.lower()), None)

if col_data:
    df_view[col_data] = pd.to_datetime(df_view[col_data], errors="coerce").dt.strftime("%d/%m/%Y")

if col_local and col_nome:
    if LOCAL_MODE:
        df_view["📂 Caminho completo"] = df_view.apply(
            lambda x: f'<a href="file:///{urllib.parse.quote(str(x[col_local]).replace("\\\\", "/") + "/" + str(x[col_nome]))}" target="_blank">{x[col_local]}</a>',
            axis=1
        )
    else:
        def make_copy_button(path, name):
            full_path = f"{path}\\{name}"
            return f'<button class="copy-btn" onclick="navigator.clipboard.writeText(\'{full_path}\')">📋 Copiar caminho</button>'
        df_view["📂 Caminho completo"] = df_view.apply(
            lambda x: make_copy_button(str(x[col_local]), str(x[col_nome])),
            axis=1
        )

cols_to_show = [col_nome, "Tamanho", "Porcentagem", "📂 Caminho completo", col_data]
cols_to_show = [c for c in cols_to_show if c in df_view.columns]
st.markdown(df_view[cols_to_show].to_html(escape=False, index=False), unsafe_allow_html=True)

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

st.markdown("---")
st.caption("Desenvolvido com 💚 em Streamlit · All Files Finder - Felipe")
