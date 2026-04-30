import streamlit as st
import pandas as pd
from PIL import Image
from fpdf import FPDF
from io import BytesIO
import google.generativeai as genai
import re
import json

st.set_page_config(page_title="Gestor de Leads", layout="centered")
st.title("Gestor de Leads")

# --- BUSCA A CHAVE SALVA NAS SECRETS ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("Erro: A chave GEMINI_API_KEY não foi configurada nas Secrets do Streamlit.")
    st.stop()

# Função de Leitura Inteligente do Google
def extrair_dados_com_ia(imagem):
    prompt = """
    Você é um leitor óptico de tabelas perfeito.
    Analise esta imagem e extraia os dados de contatos.
    Identifique cada linha horizontal da tabela.
    Extraia as informações de texto (Nome e Sobrenome) e o Telefone que estão estritamente na mesma linha.
    Mantenha a informação da mesma linha horizontal junta. Não misture o telefone de uma pessoa com o nome de outra.
    Retorne o resultado estritamente no formato JSON abaixo, sem textos extras ou explicações:
    [
      {"Informação": "NOME SOBRENOME", "Telefone": "DDD + NÚMERO"},
      {"Informação": "OUTRO NOME", "Telefone": "DDD + NÚMERO"}
    ]
    """
    
    try:
        response = model.generate_content([prompt, imagem])
        texto_resposta = response.text
        
        # Filtro para pegar apenas o JSON da resposta
        match = re.search(r'\[.*\]', texto_resposta, re.DOTALL)
        if match:
            dados_json = json.loads(match.group(0))
            return pd.DataFrame(dados_json)
        else:
            st.error("A IA não conseguiu estruturar os dados no formato esperado.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return pd.DataFrame()

# 1. Upload
arquivo = st.file_uploader("Carregar Foto da Tabela ou Planilha", type=["xlsx", "csv", "jpg", "png", "jpeg"])

if arquivo:
    if "dados" not in st.session_state:
        if arquivo.type in ["image/jpeg", "image/png"]:
            with st.spinner("Lendo foto..."):
                img = Image.open(arquivo)
                df_extraido = extrair_dados_com_ia(img)
                if df_extraido.empty:
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
        st.markdown("---")
        st.subheader(f"Lead #{p + 1}")
        
        contato = df.iloc[p]
        with st.container(border=True):
            info_atual = contato.get('Informação', contato.get('Nome', 'Sem dados'))
            st.write(f"👤 **Dados:** {info_atual}")
            
            tel_bruto = str(contato.get('Telefone', ''))
            tel_limpo = "".join(filter(str.isdigit, tel_bruto))
            
            st.write(f"📞 **Telefone:** {tel_bruto if tel_bruto else 'Não identificado'}")

            if len(tel_limpo) >= 8:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'''<a href="tel:{tel_limpo}" style="text-decoration:none;">
                        <button style="width:100%; border-radius:10px; background-color:#25D366; color:white; border:none; padding:12px; font-weight:bold;">
                        📞 Ligar</button></a>''', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'''<a href="https://wa.me/55{tel_limpo}" target="_blank" style="text-decoration:none;">
                        <button style="width:100%; border-radius:10px; background-color:#128C7E; color:white; border:none; padding:12px; font-weight:bold;">
                        💬 WhatsApp</button></a>''', unsafe_allow_html=True)

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

    # 3. Exportação
    st.divider()
    formato = st.radio("Escolha o formato:", ["Excel", "PDF"], horizontal=True)

    if st.button("💾 Gerar Arquivo Final"):
        if formato == "Excel":
            output = BytesIO()
            df.to_excel(output, index=False)
            st.download_button("Baixar Excel", output.getvalue(), "resultado.xlsx")
        else:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", "B", 14)
            pdf.cell(0, 10, "Relatorio de Leads", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("helvetica", size=10)
            
            for i, row in df.iterrows():
                if row['Status'] == 'Potencial':
                    pdf.set_text_color(0, 128, 0)
                elif row['Status'] == 'Descartado':
                    pdf.set_text_color(255, 0, 0)
                else:
                    pdf.set_text_color(0, 0, 0)
                
                info_texto = row.get('Informação', row.get('Nome', 'Sem dados'))
                texto_linha = f"#{i+1} [{row['Status']}] - {info_texto}"
                pdf.multi_cell(0, 8, texto_linha.encode('latin-1', 'ignore').decode('latin-1'), border=1)
                pdf.ln(2)
            
            st.download_button("Baixar PDF", bytes(pdf.output()), "resultado.pdf")
