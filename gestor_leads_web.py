import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageOps
import pytesseract
from fpdf import FPDF
from io import BytesIO
import re

st.set_page_config(page_title="Gestor de Leads", layout="centered")
st.title("Gestor de Leads")

def extrair_dados_da_foto(imagem):
    # Otimização para leitura linear
    imagem = ImageOps.grayscale(imagem)
    imagem = ImageOps.autocontrast(imagem)
    
    # O segredo: pedimos os dados detalhados (com coordenadas X, Y)
    dados_ocr = pytesseract.image_to_data(imagem, lang='por', output_type=pytesseract.Output.DICT)
    
    n_boxes = len(dados_ocr['text'])
    linhas_agrupadas = {}

    # Agrupa o texto por posição vertical (Y), com margem de erro de 10 pixels
    # Isso simula a "linha reta" que você pediu
    for i in range(n_boxes):
        if int(dados_ocr['conf'][i]) > 30: # Só pega o que tiver confiança de leitura
            y = dados_ocr['top'][i] // 15 # Agrupa palavras na mesma altura
            texto = dados_ocr['text'][i].strip()
            if texto:
                if y not in linhas_agrupadas:
                    linhas_agrupadas[y] = []
                linhas_agrupadas[y].append(texto)

    lista_final = []
    # Processa cada "linha reta" identificada
    for y in sorted(linhas_agrupadas.keys()):
        linha_completa = " ".join(linhas_agrupadas[y])
        
        # Procura o telefone na linha (10 ou 11 dígitos)
        nums = "".join(re.findall(r'\d+', linha_completa))
        
        if 10 <= len(nums) <= 12:
            # O que é texto na linha vira o Nome
            nome = re.sub(r'\d+', '', linha_completa).replace('(', '').replace(')', '').replace('-', '').strip()
            
            # Formatação
            ddd = nums[:2]
            corpo = nums[2:]
            tel_visual = f"({ddd}) {corpo[:5]}-{corpo[5:]}" if len(corpo) == 9 else f"({ddd}) {corpo[:4]}-{corpo[4:]}"
            
            lista_final.append({
                "Nome": nome if len(nome) > 2 else "Lead",
                "Telefone": tel_visual,
                "Tel_Acao": nums,
                "Status": "Pendente"
            })

    return pd.DataFrame(lista_final)

# --- RESTO DA INTERFACE ---
arquivo = st.file_uploader("Carregar Lista ou Foto", type=["xlsx", "csv", "jpg", "png", "jpeg"])

if arquivo:
    if "dados" not in st.session_state:
        if arquivo.type in ["image/jpeg", "image/png"]:
            with st.spinner("Lendo linhas da imagem..."):
                img = Image.open(arquivo)
                st.session_state.dados = extrair_dados_da_foto(img)
        else:
            st.session_state.dados = pd.read_excel(arquivo) if arquivo.name.endswith('.xlsx') else pd.read_csv(arquivo)
            if 'Status' not in st.session_state.dados.columns:
                st.session_state.dados['Status'] = 'Pendente'
        st.session_state.ponteiro = 0

    df = st.session_state.dados
    p = st.session_state.ponteiro

    if p < len(df):
        st.markdown("---")
        st.subheader(f"Lead #{p + 1}")
        contato = df.iloc[p]
        
        with st.container(border=True):
            st.write(f"**NOME:** {contato.get('Nome', 'Não identificado')}")
            st.write(f"**TEL:** {contato.get('Telefone', '')}")
            
            num = "".join(filter(str.isdigit, str(contato.get('Tel_Acao', ''))))
            if num:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'<a href="tel:{num}"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold;">📞 Ligar</button></a>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<a href="https://wa.me{num}"><button style="width:100%; background-color:#128C7E; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold;">💬 WhatsApp</button></a>', unsafe_allow_html=True)
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🟩 OK", use_container_width=True):
                st.session_state.dados.at[p, 'Status'] = 'Potencial'; st.session_state.ponteiro += 1; st.rerun()
        with col2:
            if st.button("🟥 SAIR", use_container_width=True):
                st.session_state.dados.at[p, 'Status'] = 'Descartado'; st.session_state.ponteiro += 1; st.rerun()
        with col3:
            if st.button("⏭️", use_container_width=True):
                st.session_state.ponteiro += 1; st.rerun()
    else:
        st.success("Lista Concluída!")
        if st.button("Recomeçar"):
            st.session_state.ponteiro = 0; st.rerun()

    if st.button("Baixar Excel"):
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button("Download", output.getvalue(), "resultado.xlsx")
