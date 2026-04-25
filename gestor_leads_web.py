import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageOps
import pytesseract
from io import BytesIO
import re

st.set_page_config(page_title="Gestor de Leads", layout="centered")
st.title("Gestor de Leads")

def extrair_dados_da_foto(imagem):
    # Tratamento de imagem para remover sombras e sujeira
    imagem = ImageOps.grayscale(imagem)
    imagem = ImageOps.autocontrast(imagem)
    
    # Extração de texto puro (mais estável para evitar 'it. lt.')
    texto_puro = pytesseract.image_to_string(imagem, lang='por')
    linhas = texto_puro.split('\n')
    
    lista_final = []
    
    for linha in linhas:
        # 1. Filtra apenas os números da linha
        nums_apenas = "".join(re.findall(r'\d+', linha))
        
        # 2. SÓ SEGUE SE TIVER UM NÚMERO DE 10 OU 11 DÍGITOS (DDD + Tel)
        # Isso mata 100% dos "leads fantasmas" de sujeira
        if 10 <= len(nums_apenas) <= 11:
            # 3. Limpa o Nome: remove os números e símbolos da linha
            nome = re.sub(r'[\d\(\)\-\.]+', '', linha).strip()
            nome = nome if len(nome) > 2 else "Lead Identificado"
            
            # 4. Formatação Visual
            ddd = nums_apenas[:2]
            resto = nums_apenas[2:]
            tel_visual = f"({ddd}) {resto[:5]}-{resto[5:]}" if len(resto) == 9 else f"({ddd}) {resto[:4]}-{resto[4:]}"
            
            lista_final.append({
                "Nome": nome[:40], # Nome limpo e curto
                "Telefone": tel_visual,
                "Tel_Acao": nums_apenas,
                "Status": "Pendente"
            })

    return pd.DataFrame(lista_final)

# --- INTERFACE DE TRABALHO ---
arquivo = st.file_uploader("Carregar Lista ou Foto", type=["xlsx", "csv", "jpg", "png", "jpeg"])

if arquivo:
    if "dados" not in st.session_state:
        if arquivo.type in ["image/jpeg", "image/png"]:
            with st.spinner("Processando..."):
                img = Image.open(arquivo)
                df_extraido = extrair_dados_da_foto(img)
                if df_extraido.empty:
                    st.error("Nenhum telefone com DDD detectado. Tente uma foto mais nítida.")
                    st.stop()
                st.session_state.dados = df_extraido
        else:
            # Excel/CSV
            df_init = pd.read_excel(arquivo) if arquivo.name.endswith('.xlsx') else pd.read_csv(arquivo)
            st.session_state.dados = df_init
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
            st.write(f"👤 **NOME:** {contato.get('Nome', 'Não identificado')}")
            st.write(f"📞 **TEL:** {contato.get('Telefone', 'Sem número')}")
            
            # Pega o número puro para os botões
            tel_puro = "".join(filter(str.isdigit, str(contato.get('Tel_Acao', contato.get('Telefone', '')))))
            
            if len(tel_puro) >= 10:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'<a href="tel:{tel_puro}"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold;">📞 Ligar</button></a>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<a href="https://wa.me{tel_puro}"><button style="width:100%; background-color:#128C7E; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold;">💬 WhatsApp</button></a>', unsafe_allow_html=True)

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
        if st.button("Reiniciar"):
            st.session_state.ponteiro = 0; st.rerun()

    if st.button("Baixar Excel Final"):
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button("Clique aqui para Baixar", output.getvalue(), "resultado.xlsx")
