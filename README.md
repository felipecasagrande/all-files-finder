
# All Files Finder - Felipe

Painel online (Streamlit) para **fazer upload de planilhas CSV/XLSX** e **filtrar registros** por nome de arquivo, extensão, data, tamanho, pasta e muito mais. Tudo **sem rodar nada localmente** — basta publicar no Streamlit Cloud.

## 🚀 Como publicar no Streamlit Cloud
1. Crie um repositório no GitHub (por exemplo `all-files-finder`).
2. Envie estes arquivos para o repositório:
   - `streamlit_app.py`
   - `requirements.txt`
   - `README.md`
3. Acesse [https://share.streamlit.io](https://share.streamlit.io) e conecte sua conta ao GitHub.
4. Clique em **New app** → selecione seu repositório e o branch principal.
5. No campo **Main file path**, informe `streamlit_app.py`.
6. Clique em **Deploy**. Pronto! Você terá um link público do tipo:
   `https://seu-usuario-seu-repo-seu-branch.streamlit.app/`

## 🧭 Uso
1. Abra o link do app.
2. Faça **upload de um ou mais arquivos** CSV/XLSX.
3. Use a **busca principal** para localizar rapidamente por nome/caminho de arquivo.
4. Aplique **filtros avançados** (numéricos, datas, categorias) na barra lateral.
5. **Baixe** o resultado filtrado em CSV.

## 💡 Notas
- O app tenta **detectar automaticamente** a coluna de nome/arquivo.
- Colunas de datas e numéricas são **inferidas automaticamente** sempre que possível.
- Se sua planilha tiver a coluna de **tamanho em bytes**, o app mostra o **tamanho total filtrado**.
- A tabela inclui uma coluna `__source_file` para identificar de qual upload veio cada linha.

---
Feito para o Felipe · Streamlit 💚
