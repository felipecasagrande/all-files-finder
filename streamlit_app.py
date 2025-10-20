import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
import io
import json

# ======================================================
# ⚙️ CONFIGURAÇÕES INICIAIS
# ======================================================
st.set_page_config(page_title="All Files Finder - Felipe", layout="wide")
st.title("📂 All Files Finder - Felipe")
st.write("Leitura automática de planilhas **XLSX** e **CSV** diretamente da pasta do Google Drive (conectada com credencial segura).")

# ======================================================
# 🔐 CONEXÃO COM GOOGLE DRIVE
# ======================================================
try:
    creds_json = st.secrets["GCP_SA_KEY"]
    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_dict)
    service = build("drive", "v3", credentials=creds)
    FOLDER_ID = "15ToUbVb9fKNDFECffoHWGr3R22_sj4Fy"
except Exception as e:
    st.error(f"⚠️ Erro ao carregar credenciais do Google Drive: {e}")
    st.stop()

# ======================================================
# 📁 LISTAR ARQUIVOS NA PASTA
# ======================================================
try:
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and (mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='text/csv')",
        fields="files(id, name, mimeType, size)",
    ).execute()

    files = results.get("files", [])
    if not files:
        st.warning("⚠️ Nenhum arquivo Excel ou CSV encontrado na pasta do Google Drive.")
        st.stop()

    file_options = {f["name"]: f for f in files}
    selected_file = st.selectbox("📄 Selecione um arquivo para abrir:", list(file_options.keys()))

    file_id = file_options[selected_file]["id"]
    mime_type = file_options[selected_file]["mimeType"]

    st.info(f"Abrindo: **{selected_file}**")

    request = service.files().get_media(fileId=file_id)
    file_data = io.BytesIO(request.execute())

    # ======================================================
    # 📑 LEITURA DO ARQUIVO
    # ======================================================
    if mime_type == "text/csv" or selected_file.lower().endswith(".csv"):
        df = pd.read_csv(file_data, encoding="utf-8", sep=None, engine="python")
    else:
        df = pd.read_excel(file_data)

    st.success(f"✅ Arquivo carregado com {df.shape[0]} linhas e {df.shape[1]} colunas.")
    st.dataframe(df.head(100), use_container_width=True)

    # ======================================================
    # 🎯 FILTROS
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

    st.markdown("---")
    st.caption("Desenvolvido com ❤️ em Streamlit · All Files Finder - Felipe")

except Exception as e:
    st.error(f"⚠️ Erro ao processar arquivos do Google Drive: {e}")
