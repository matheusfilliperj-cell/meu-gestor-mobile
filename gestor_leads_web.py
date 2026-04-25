import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from io import BytesIO
import re

st.set_page_config(page_title="Gestor de Leads", layout="centered")

def extrair_tabela_da_foto(imagem):
    # 1. Tratamento para destacar o contraste das linhas
    imagem = ImageOps.grayscale(imagem)
    imagem = imagem.filter(ImageFilter.SHARPEN)
    
    # 2. Configuração para manter a estrutura de colunas (preserve_interword_spaces)
    config_tess = "--psm 6" # Modo que assume um bloco de texto/tabela único
    texto_puro = pytesseract.image_to_string(imagem, lang='por', config=config_tess)
    linhas = texto_puro.split('\n')
    
    lista_final = []
    
    for linha in linhas:
        # Extrai todos os números da linha
        numeros_na_linha = "".join(re.findall(r'\d+', linha))
        
        # Filtro: Só processa linhas que tenham um telefone (10 ou 11 dígitos)
        if 10 <= len(numeros_na_linha) <= 12:
            # Tenta separar por grandes espaços (comum em tabelas escaneadas)
            partes = re.split(r'\s{2,}', linha.strip())
            
            if len(partes) >= 2:
                # Se tiver 3 ou mais partes, mapeia como Nome, Sobrenome e Tel
                nome = partes[0]
                sobrenome = partes[1] if len(partes) > 2 else ""
                # O telefone é sempre a última parte numérica identificada
                tel_visual = f"({numeros_na_linha[:2]}) {numeros_na_linha[2:]}"
            else:
                # Caso o OCR junte tudo, tentamos separar o texto do número no final
                nome_bruto = re.sub(r'\d+', '', linha).replace('(', '').replace(')', '').replace('-', '').strip()
                nome = nome_bruto.split()[0] if nome_bruto.split() else "Lead"
                sobrenome = " ".join(nome_bruto.split()[1:]) if len(nome_bruto.split()) > 1 else ""
                tel_visual = f"({numeros_na_linha[:2]}) {numeros_na_linha[2:]}"

            lista_final.append({
                "Nome": nome.upper(),
                "Sobrenome": sobrenome.upper(),
                "Telefone": tel_visual,
                "Tel_Acao": numeros_na_linha[:11], # Limita a 11 dígitos
                "Status": "Pendente"
            })

    return pd.DataFrame(lista_final)

# --- INTERFACE DE TRABALHO ---
st.title("📞 Gestor de Leads")

arquivo = st.file_uploader("Suba a Foto da Tabela ou Planilha", type=["xlsx", "csv", "jpg", "png", "jpeg"])

if arquivo:
    if "dados" not in st.session_state:
        if arquivo.type in ["image/jpeg", "image/png"]:
            with st.spinner("Analisando colunas da tabela..."):
                img = Image.open(arquivo)
                df_res = extrair_tabela_da_foto(img)
                if df_res.empty:
                    st.error("Não foi possível identificar a tabela. Tire a foto mais de perto.")
                    st.stop()
                st.session_state.dados = df_res
        else:
            df_init = pd.read_excel(arquivo) if arquivo.name.endswith('.xlsx') else pd.read_csv(arquivo)
            st.session_state.dados = df_init
            if 'Status' not in st.session_state.dados.columns:
                st.session_state.dados['Status'] = 'Pendente'
        st.session_state.ponteiro = 0

    df = st.session_state.dados
    p = st.session_state.ponteiro

    if p < len(df):
        contato = df.iloc[p]
        st.markdown(f"### Lead #{p + 1}")
        
        with st.container(border=True):
            st.subheader(f"{contato.get('Nome', '')} {contato.get('Sobrenome', '')}")
            st.markdown(f"#### 📞 {contato.get('Telefone', 'Sem número')}")
            
            tel_btn = "".join(filter(str.isdigit, str(contato.get('Tel_Acao', ''))))

            if len(tel_btn) >= 10:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'<a href="tel:{tel_btn}"><button style="width:100%; height:50px; background-color:#28a745; color:white; border:none; border-radius:8px; font-weight:bold;">LIGAR</button></a>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<a href="https://wa.me{tel_btn}"><button style="width:100%; height:50px; background-color:#25d366; color:white; border:none; border-radius:8px; font-weight:bold;">WHATSAPP</button></a>', unsafe_allow_html=True)

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🟩 POTENCIAL", use_container_width=True):
                st.session_state.dados.at[p, 'Status'] = 'Potencial'; st.session_state.ponteiro += 1; st.rerun()
        with col2:
            if st.button("🟥 DESCARTAR", use_container_width=True):
                st.session_state.dados.at[p, 'Status'] = 'Descartado'; st.session_state.ponteiro += 1; st.rerun()
        with col3:
            if st.button("⏭️ PULAR", use_container_width=True):
                st.session_state.ponteiro += 1; st.rerun()
    else:
        st.success("Lista Finalizada!")
        if st.button("Recomeçar"):
            st.session_state.ponteiro = 0; st.rerun()

    if st.button("Baixar Excel Atualizado"):
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button("Clique aqui para baixar", output.getvalue(), "leads_final.xlsx")
