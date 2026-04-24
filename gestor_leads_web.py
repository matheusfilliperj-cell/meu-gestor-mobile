import streamlit as st
import pandas as pd
from io import BytesIO
import pdfkit
import os
import shutil

# --- CONFIGURAÇÃO DE AMBIENTE (Nuvem vs Local) ---
# Na nuvem (Linux), o comando 'which' encontra o motor de PDF automaticamente
path_wkhtmltopdf = shutil.which("wkhtmltopdf")
if not path_wkhtmltopdf:
    # Caso você rode no PC para testes, ele busca na sua pasta local
    path_wkhtmltopdf = os.path.join(os.path.abspath("."), "wkhtmltopdf", "bin", "wkhtmltopdf.exe")

try:
    config_pdf = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
except:
    config_pdf = None

st.set_page_config(page_title="Gestor Leads Mobile", layout="centered")

st.title("📱 Gestor de Leads Mobile")

# 1. Carregamento
arquivo = st.file_uploader("Carregar Lista (Excel/CSV)", type=["xlsx", "csv"])

if arquivo:
    if "dados" not in st.session_state:
        if arquivo.name.endswith('.csv'):
            st.session_state.dados = pd.read_csv(arquivo)
        else:
            st.session_state.dados = pd.read_excel(arquivo)
        st.session_state.dados['Status'] = 'Pendente'
        st.session_state.ponteiro = 0

    df = st.session_state.dados
    p = st.session_state.ponteiro

    if p < len(df):
        st.markdown(f"### 👤 Contato {p + 1} de {len(df)}")
        contato = df.iloc[p]
        
        # Exibição Card (Melhor para celular que tabela)
        with st.container(border=True):
            st.write(f"**Nome:** {contato.get('Nome', 'N/A')} {contato.get('Sobrenome', '')}")
            tel = str(contato.get('Telefone', '')).replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
            st.write(f"**Tel:** {contato.get('Telefone', 'N/A')}")
            
            # --- BOTÕES DE AÇÃO RÁPIDA (O pulo do gato no mobile) ---
            col_a, col_b = st.columns(2)
            with col_a:
                # Botão para ligar direto
                st.markdown(f'''<a href="tel:{tel}" style="text-decoration:none;">
                    <button style="width:100%; border-radius:10px; background-color:#25D366; color:white; border:none; padding:10px;">
                    📞 Ligar Agora</button></a>''', unsafe_allow_html=True)
            with col_b:
                # Botão para WhatsApp direto
                st.markdown(f'''<a href="https://wa.me{tel}" target="_blank" style="text-decoration:none;">
                    <button style="width:100%; border-radius:10px; background-color:#128C7E; color:white; border:none; padding:10px;">
                    💬 WhatsApp</button></a>''', unsafe_allow_html=True)

        st.divider()

        # Decisão de Status
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🟩 OK", use_container_width=True):
                st.session_state.dados.at[p, 'Status'] = 'Potencial'
                st.session_state.ponteiro += 1
                st.rerun()
        with c2:
            if st.button("🟥 SAIR", use_container_width=True):
                st.session_state.dados.at[p, 'Status'] = 'Descartado'
                st.session_state.ponteiro += 1
                st.rerun()
        with c3:
            if st.button("⏭️", use_container_width=True):
                st.session_state.ponteiro += 1
                st.rerun()
    else:
        st.success("🏁 Lista Concluída!")

    # Exportação
    st.divider()
    formato = st.radio("Exportar em:", ["Excel", "PDF"], horizontal=True)
    
    if st.button("📥 Baixar Arquivo Final"):
        # (Lógica de cores igual a anterior...)
        def aplicar_cor(row):
            if row['Status'] == 'Potencial': return ['background-color: #90EE90'] * len(row)
            if row['Status'] == 'Descartado': return ['background-color: #FF7F7F'] * len(row)
            return [''] * len(row)
        
        df_colorido = df.style.apply(aplicar_cor, axis=1)
        
        if formato == "Excel":
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_colorido.to_excel(writer, index=False)
            st.download_button("Download Excel", output.getvalue(), "leads_mobile.xlsx")
        else:
            html = df_colorido.to_html()
            pdf = pdfkit.from_string(html, False, configuration=config_pdf)
            st.download_button("Download PDF", pdf, "leads_mobile.pdf")
