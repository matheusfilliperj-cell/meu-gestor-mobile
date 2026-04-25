import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageOps
import pytesseract
from fpdf import FPDF
from io import BytesIO
import re

# --- INTERFACE ---
st.set_page_config(page_title="Gestor de Leads", layout="centered")

st.title("Gestor de Leads")

# Função de extração cirúrgica via Âncora de DDD
def extrair_dados_da_foto(imagem):
    # Otimização de imagem para contraste máximo
    imagem = ImageOps.grayscale(imagem)
    imagem = ImageOps.autocontrast(imagem)
    texto_extraido = pytesseract.image_to_string(imagem, lang='por')
    linhas = texto_extraido.split('\n')
    
    lista_organizada = []
    
    for linha in linhas:
        # Procuramos o padrão do parênteses do DDD como âncora
        if '(' in linha:
            # Separa o Nome (tudo antes do parênteses)
            partes_nome = linha.split('(', 1)
            nome_limpo = partes_nome[0].strip()
            
            # Separa o Telefone (o parênteses e tudo que vem depois)
            # Removemos qualquer caractere que não seja número para a ação de ligar
            resto_linha = partes_nome[1]
            numeros_tel = "".join(re.findall(r'\d+', resto_linha))
            
            # Validação: Só aceita se tiver cara de número com DDD (10 ou 11 dígitos)
            if 10 <= len(numeros_tel) <= 11:
                # Formatação Visual para a tela
                ddd = numeros_tel[:2]
                corpo = numeros_tel[2:]
                tel_formatado = f"({ddd}) {corpo[:5]}-{corpo[5:]}" if len(corpo) == 9 else f"({ddd}) {corpo[:4]}-{corpo[4:]}"
                
                lista_organizada.append({
                    "Nome": nome_limpo if len(nome_limpo) > 2 else "Contato Identificado",
                    "Telefone": tel_formatado,
                    "Tel_Acao": numeros_tel,
                    "Status": "Pendente"
                })

    return pd.DataFrame(lista_organizada) if lista_organizada else pd.DataFrame()

# 1. Upload
arquivo = st.file_uploader("Carregar Arquivo ou Foto", type=["xlsx", "csv", "jpg", "png", "jpeg"])

if arquivo:
    if "dados" not in st.session_state:
        if arquivo.type in ["image/jpeg", "image/png"]:
            with st.spinner("Processando..."):
                img = Image.open(arquivo)
                df_extraido = extrair_dados_da_foto(img)
                if df_extraido.empty:
                    st.error("Nenhum lead com DDD entre parênteses '(' encontrado na imagem.")
                    st.stop()
                st.session_state.dados = df_extraido
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

    # 2. Área de Trabalho
    if p < len(df):
        st.info(f"Lead {p + 1} de {len(df)}")
        contato = df.iloc[p]
        
        with st.container(border=True):
            st.subheader(contato.get("Nome", "Lead"))
            st.write(f"📞 **{contato.get('Telefone', 'Sem número')}**")
            
            # Extração de número puro para os botões
            num_limpo = str(contato.get('Tel_Acao', contato.get('Telefone', '')))
            num_limpo = "".join(filter(str.isdigit, num_limpo))

            if len(num_limpo) >= 10:
                c_ligar, c_zap = st.columns(2)
                with c_ligar:
                    st.markdown(f'''<a href="tel:{num_limpo}" style="text-decoration:none;">
                        <button style="width:100%; border-radius:10px; background-color:#25D366; color:white; border:none; padding:12px; font-weight:bold;">
                        📞 Ligar</button></a>''', unsafe_allow_html=True)
                with c_zap:
                    st.markdown(f'''<a href="https://wa.me{num_limpo}" target="_blank" style="text-decoration:none;">
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
        st.success("Lista Concluída!")
        if st.button("Reiniciar"):
            st.session_state.ponteiro = 0
            st.rerun()

    # 3. Exportação
    st.divider()
    formato = st.radio("Exportar:", ["Excel", "PDF"], horizontal=True)

    if st.button("Gerar Relatório"):
        if formato == "Excel":
            output = BytesIO()
            def aplicar_cor(row):
                if row['Status'] == 'Potencial': return ['background-color: #90EE90'] * len(row)
                if row['Status'] == 'Descartado': return ['background-color: #FF7F7F'] * len(row)
                return [''] * len(row)
            df.style.apply(aplicar_cor, axis=1).to_excel(output, index=False)
            st.download_button("Download Excel", output.getvalue(), "resultado.xlsx")
        else:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", "B", 14)
            pdf.cell(0, 10, "Relatorio de Leads", ln=True, align='C')
            pdf.set_font("helvetica", size=10)
            for _, row in df.iterrows():
                cor = (0, 128, 0) if row['Status'] == 'Potencial' else (255, 0, 0) if row['Status'] == 'Descartado' else (0, 0, 0)
                pdf.set_text_color(*cor)
                texto = f"[{row['Status']}] {row.get('Nome','')} - {row.get('Telefone','')}"
                pdf.multi_cell(0, 8, texto.encode('latin-1', 'ignore').decode('latin-1'), border=1)
            st.download_button("Download PDF", bytes(pdf.output()), "resultado.pdf")
