import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import easyocr
from fpdf import FPDF
from io import BytesIO
import re

# --- CONFIGURAÇÃO E CACHE DO LEITOR DE FOTOS ---
@st.cache_resource
def get_ocr_reader():
    return easyocr.Reader(['pt'])

def extrair_dados_da_foto(imagem):
    reader = get_ocr_reader()
    img_np = np.array(imagem)
    resultado = reader.readtext(img_np, detail=0)
    
    # Tenta organizar o texto bagunçado da foto em uma tabela básica
    # Ele busca padrões de números para tentar identificar o telefone
    lista_organizada = []
    for texto in resultado:
        telefone = re.findall(r'\d+', texto)
        tel_formatado = "".join(telefone) if telefone else ""
        lista_organizada.append({
            "Informação": texto,
            "Telefone_Detectado": tel_formatado if len(tel_formatado) >= 8 else ""
        })
    return pd.DataFrame(lista_organizada)

# --- INTERFACE ---
st.set_page_config(page_title="Gestor Leads Pro", layout="centered")

st.title("🚀 Gestor de Leads Inteligente")
st.markdown("### Suporta Excel e Fotos (OCR)")

# 1. Upload Multiformato
arquivo = st.file_uploader("Suba uma Foto, Excel ou CSV", type=["xlsx", "csv", "jpg", "png", "jpeg"])

if arquivo:
    if "dados" not in st.session_state:
        # Lógica para Fotos
        if arquivo.type in ["image/jpeg", "image/png"]:
            with st.spinner("🤖 IA escaneando a foto... aguarde."):
                img = Image.open(arquivo)
                st.session_state.dados = extrair_dados_da_foto(img)
        
        # Lógica para Planilhas
        else:
            if arquivo.name.endswith('.csv'):
                st.session_state.dados = pd.read_csv(arquivo)
            else:
                st.session_state.dados = pd.read_excel(arquivo)
        
        if 'Status' not in st.session_state.dados.columns:
            st.session_state.dados['Status'] = 'Pendente'
        st.session_state.ponteiro = 0

    df = st.session_state.dados
    p = st.session_state.ponteiro

    # 2. Área de Trabalho (Lead por Lead)
    if p < len(df):
        st.info(f"📍 Lead {p + 1} de {len(df)}")
        contato = df.iloc[p]
        
        with st.container(border=True):
            # Exibe as informações da linha
            for col in df.columns:
                if col != 'Status':
                    st.write(f"**{col}:** {contato[col]}")
            
            # Limpeza do número para ação direta
            # Tenta pegar o telefone da coluna específica ou de qualquer campo que tenha número
            txt_para_tel = str(contato.get('Telefone', contato.get('Telefone_Detectado', '')))
            tel_limpo = "".join(filter(str.isdigit, txt_para_tel))

            if len(tel_limpo) >= 8:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f'''<a href="tel:{tel_limpo}" style="text-decoration:none;">
                        <button style="width:100%; border-radius:10px; background-color:#25D366; color:white; border:none; padding:12px; font-weight:bold;">
                        📞 Ligar</button></a>''', unsafe_allow_html=True)
                with col_b:
                    st.markdown(f'''<a href="https://wa.me{tel_limpo}" target="_blank" style="text-decoration:none;">
                        <button style="width:100%; border-radius:10px; background-color:#128C7E; color:white; border:none; padding:12px; font-weight:bold;">
                        💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Nenhum telefone válido detectado nesta linha.")

        st.divider()
        
        # Botões de Status
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
        st.success("🏁 Fim da lista!")
        if st.button("Recomeçar"):
            st.session_state.ponteiro = 0
            st.rerun()

    # 3. Exportação
    st.divider()
    formato = st.radio("Exportar resultado em:", ["Excel", "PDF"], horizontal=True)

    if st.button("💾 Baixar Relatório Colorido"):
        if formato == "Excel":
            output = BytesIO()
            def aplicar_cor(row):
                if row['Status'] == 'Potencial': return ['background-color: #90EE90'] * len(row)
                if row['Status'] == 'Descartado': return ['background-color: #FF7F7F'] * len(row)
                return [''] * len(row)
            df.style.apply(aplicar_cor, axis=1).to_excel(output, index=False)
            st.download_button("Download Excel", output.getvalue(), "leads_final.xlsx")
        
        else:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", "B", 14)
            pdf.cell(0, 10, "Relatorio de Leads - Gestor Mobile", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("helvetica", size=10)
            
            for _, row in df.iterrows():
                cor = (0, 128, 0) if row['Status'] == 'Potencial' else (255, 0, 0) if row['Status'] == 'Descartado' else (0, 0, 0)
                pdf.set_text_color(*cor)
                texto = " | ".join([str(v) for v in row.values])
                pdf.multi_cell(0, 8, texto, border=1)
                pdf.ln(2)
            
            pdf_out = pdf.output()
            st.download_button("Download PDF", bytes(pdf_out), "leads_final.pdf")
