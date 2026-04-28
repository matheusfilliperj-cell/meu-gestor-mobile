import streamlit as st
import pandas as pd
from PIL import Image
from fpdf import FPDF
from io import BytesIO
import google.generativeai as genai
import json
import re

st.set_page_config(page_title="Gestor de Leads IA", layout="centered")
st.title("🤖 Gestor de Leads com IA")

# 1. Configuração da Chave
api_key = st.secrets["GEMINI_API_KEY"]

if api_key:
    genai.configure(api_key=api_key)
    # Usando o modelo 1.5-flash que é ultra rápido para fotos
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.warning("⚠️ Insira sua API Key para liberar a leitura de fotos.")

# 2. Função de Leitura Inteligente e Rápida
def extrair_dados_com_ia(imagem):
    # Reduz o tamanho da imagem para enviar mais rápido
    imagem.thumbnail((800, 800))
    
    prompt = """
    Analise esta imagem e extraia os dados de contatos em formato de tabela.
    Mantenha rigorosamente a informação da mesma linha horizontal junta. 
    Retorne o resultado estritamente no formato JSON abaixo, sem textos extras, sem saudações e sem aspas de bloco de código (```json):
    [
      {"Nome": "NOME COMPLETO", "Telefone": "DDD + NUMERO"}
    ]
    """
    
    try:
        response = model.generate_content([prompt, imagem])
        texto_resposta = response.text
        
        # Limpeza agressiva para pegar apenas o que está dentro dos colchetes [ ]
        match = re.search(r'\[.*\]', texto_resposta, re.DOTALL)
        if match:
            dados_json = json.loads(match.group(0))
            return pd.DataFrame(dados_json)
        else:
            st.error("A IA não gerou uma resposta no formato correto.")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return pd.DataFrame()

# 1. Upload
arquivo = st.file_uploader("Carregar Foto da Tabela ou Planilha", type=["xlsx", "csv", "jpg", "png", "jpeg"])

if arquivo:
    if "dados" not in st.session_state:
        if arquivo.type in ["image/jpeg", "image/png"]:
            if not api_key:
                st.error("Insira a API Key primeiro!")
                st.stop()
            with st.spinner("🤖 O Gemini está lendo a sua foto com precisão..."):
                img = Image.open(arquivo)
                df_extraido = extrair_dados_com_ia(img)
                if df_extraido.empty:
                    st.error("A IA não conseguiu estruturar os dados. Tente uma foto mais nítida.")
                    st.stop()
                st.session_state.dados = df_extraido
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

    # 2. Área de Trabalho (Lead por Lead)
    if p < len(df):
        st.info(f"Lead {p + 1} de {len(df)}")
        contato = df.iloc[p]
        
        with st.container(border=True):
            st.subheader(contato.get("Nome", "Cliente"))
            st.write(f"📞 **{contato.get('Telefone', 'Sem número')}**")
            
            # Limpeza do telefone para os botões
            tel_bruto = str(contato.get('Telefone', ''))
            tel_limpo = "".join(filter(str.isdigit, tel_bruto))

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

        st.divider()
        
        # Botões de Status
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🟩 OK", use_container_width=True):
                st.session_state.dados.at[p, 'Status'] = 'Potencial'; st.session_state.ponteiro += 1; st.rerun()
        with c2:
            if st.button("🟥 SAIR", use_container_width=True):
                st.session_state.dados.at[p, 'Status'] = 'Descartado'; st.session_state.ponteiro += 1; st.rerun()
        with c3:
            if st.button("⏭️", use_container_width=True):
                st.session_state.ponteiro += 1; st.rerun()
    else:
        st.success("Lista Concluída!")
        if st.button("Recomeçar"):
            st.session_state.ponteiro = 0; st.rerun()

    # 3. Exportação (Excel e PDF)
    st.divider()
    formato = st.radio("Exportar em:", ["Excel", "PDF"], horizontal=True)

    if st.button("Gerar Arquivo Final"):
        if formato == "Excel":
            output = BytesIO()
            df.to_excel(output, index=False)
            st.download_button("Baixar Excel", output.getvalue(), "leads.xlsx")
        else:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", "B", 14)
            pdf.cell(0, 10, "Relatório de Leads", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("helvetica", size=10)
            
            for _, row in df.iterrows():
                cor = (0, 128, 0) if row['Status'] == 'Potencial' else (255, 0, 0) if row['Status'] == 'Descartado' else (0, 0, 0)
                pdf.set_text_color(*cor)
                texto = f"[{row['Status']}] {row.get('Nome','')} - {row.get('Telefone','')}"
                pdf.multi_cell(0, 8, texto.encode('latin-1', 'ignore').decode('latin-1'), border=1)
            
            st.download_button("Baixar PDF", bytes(pdf.output()), "leads.pdf")
