import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageOps
import pytesseract
from fpdf import FPDF
from io import BytesIO
import re

# --- INTERFACE ---
st.set_page_config(page_title="Gestor Leads Pro", layout="centered")

st.title("🚀 Gestor de Leads Inteligente")
st.markdown("### Leitor de Fotos Ultra-Robusto")

# Função de extração "Blindada"
def extrair_dados_da_foto(imagem):
    # Pré-processamento da imagem para melhorar o OCR (Cinza e Contraste)
    imagem = ImageOps.grayscale(imagem)
    texto_extraido = pytesseract.image_to_string(imagem, lang='por')
    linhas = texto_extraido.split('\n')
    
    lista_organizada = []
    
    for linha in linhas:
        # 1. Limpa tudo que não é número para validar o telefone
        numeros_apenas = "".join(re.findall(r'\d+', linha))
        
        # 2. VALIDAÇÃO ROBUSTA: 
        # No Brasil, um lead útil com DDD tem 10 (fixo) ou 11 (celular) dígitos.
        # Ignoramos qualquer linha que tenha menos de 10 ou mais de 12 (ruído/datas)
        if 10 <= len(numeros_apenas) <= 11:
            # Formata para exibição: (XX) XXXXX-XXXX
            ddd = numeros_apenas[:2]
            resto = numeros_apenas[2:]
            if len(resto) == 9: # Celular
                tel_formatado = f"({ddd}) {resto[:5]}-{resto[5:]}"
            else: # Fixo
                tel_formatado = f"({ddd}) {resto[:4]}-{resto[4:]}"

            # Tenta pegar o Nome (remove os números da linha para sobrar o texto)
            nome_provavel = re.sub(r'\d+', '', linha).replace('(', '').replace(')', '').replace('-', '').strip()
            # Se o nome for muito curto ou vazio, coloca "Contato Identificado"
            nome_final = nome_provavel if len(nome_provavel) > 2 else "Lead via Foto"

            lista_organizada.append({
                "Nome/Info": nome_final[:30], # Limita tamanho para não quebrar layout
                "Telefone": tel_formatado,
                "Status": "Pendente",
                "Tel_Limpo": numeros_apenas # Guardamos para o link do Zap
            })

    # Cria o DataFrame apenas com o que passou no filtro
    if lista_organizada:
        return pd.DataFrame(lista_organizada)
    else:
        return pd.DataFrame([{"Nome/Info": "Nenhum lead válido encontrado", "Telefone": "Verifique a foto", "Status": "Pendente", "Tel_Limpo": ""}])

# 1. Upload
arquivo = st.file_uploader("Suba uma Foto, Excel ou CSV", type=["xlsx", "csv", "jpg", "png", "jpeg"])

if arquivo:
    if "dados" not in st.session_state:
        if arquivo.type in ["image/jpeg", "image/png"]:
            with st.spinner("🤖 Escaneando e filtrando leads..."):
                img = Image.open(arquivo)
                st.session_state.dados = extrair_dados_da_foto(img)
        else:
            # Lógica para Excel/CSV
            if arquivo.name.endswith('.csv'):
                st.session_state.dados = pd.read_csv(arquivo)
            else:
                st.session_state.dados = pd.read_excel(arquivo)
            if 'Status' not in st.session_state.dados.columns:
                st.session_state.dados['Status'] = 'Pendente'
        
        st.session_state.ponteiro = 0

    df = st.session_state.dados
    p = st.session_state.ponteiro

    # 2. Área de Trabalho
    if p < len(df):
        st.info(f"📍 Lead {p + 1} de {len(df)}")
        contato = df.iloc[p]
        
        with st.container(border=True):
            st.subheader(contato.get("Nome/Info", "Lead"))
            st.write(f"📞 **{contato.get('Telefone', 'Sem número')}**")
            
            # Pega o número limpo (da planilha ou do OCR)
            tel_acao = str(contato.get('Tel_Limpo', contato.get('Telefone', '')))
            tel_acao = "".join(filter(str.isdigit, tel_acao))

            if len(tel_acao) >= 10:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f'''<a href="tel:{tel_acao}" style="text-decoration:none;">
                        <button style="width:100%; border-radius:10px; background-color:#25D366; color:white; border:none; padding:12px; font-weight:bold;">
                        📞 Ligar</button></a>''', unsafe_allow_html=True)
                with col_b:
                    st.markdown(f'''<a href="https://wa.me{tel_acao}" target="_blank" style="text-decoration:none;">
                        <button style="width:100%; border-radius:10px; background-color:#128C7E; color:white; border:none; padding:12px; font-weight:bold;">
                        💬 WhatsApp</button></a>''', unsafe_allow_html=True)

        st.divider()
        
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
    formato = st.radio("Exportar:", ["Excel", "PDF"], horizontal=True)

    if st.button("💾 Baixar Relatório"):
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
            pdf.cell(0, 10, "Relatorio de Leads", ln=True, align='C')
            pdf.set_font("helvetica", size=10)
            for _, row in df.iterrows():
                cor = (0, 128, 0) if row['Status'] == 'Potencial' else (255, 0, 0) if row['Status'] == 'Descartado' else (0, 0, 0)
                pdf.set_text_color(*cor)
                texto = f"[{row['Status']}] {row.get('Nome/Info','')} - {row.get('Telefone','')}"
                pdf.multi_cell(0, 8, texto, border=1)
            st.download_button("Download PDF", bytes(pdf.output()), "leads.pdf")

