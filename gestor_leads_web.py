import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import pytesseract
from fpdf import FPDF
from io import BytesIO

st.set_page_config(page_title="Gestor de Leads", layout="centered")
st.title("Gestor de Leads")

# Função que lê a linha inteira sem quebrar
def extrair_linhas_puras(imagem):
    imagem = ImageOps.grayscale(imagem)
    imagem = ImageOps.autocontrast(imagem)
    
    # Extrai o texto mantendo a ordem das linhas
    texto_puro = pytesseract.image_to_string(imagem, lang='por')
    linhas = texto_puro.split('\n')
    
    lista_final = []
    for linha in linhas:
        texto_limpo = linha.strip()
        # Ignora linhas muito curtas que costumam ser sujeira
        if len(texto_limpo) > 5:
            lista_final.append({
                "Informação": texto_limpo,
                "Status": "Pendente"
            })
            
    return pd.DataFrame(lista_final)

# 1. Upload
arquivo = st.file_uploader("Carregar Foto ou Planilha", type=["xlsx", "csv", "jpg", "png", "jpeg"])

if arquivo:
    if "dados" not in st.session_state:
        if arquivo.type in ["image/jpeg", "image/png"]:
            with st.spinner("Lendo linhas..."):
                img = Image.open(arquivo)
                df_extraido = extrair_linhas_puras(img)
                if df_extraido.empty:
                    st.error("Nenhum texto detectado. Tente uma foto mais clara.")
                    st.stop()
                st.session_state.dados = df_extraido
        else:
            st.session_state.dados = pd.read_excel(arquivo) if arquivo.name.endswith('.xlsx') else pd.read_csv(arquivo)
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
            # Mostra o texto bruto capturado na linha
            info_atual = contato.get('Informação', contato.get('Nome', 'Sem dados'))
            st.write(f"📄 **Dados:** {info_atual}")
            
            if 'Telefone' in contato:
                st.write(f"📞 **Tel:** {contato['Telefone']}")

        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🟩 OK", use_container_width=True):
                st.session_state.dados.at[p, 'Status'] = 'Potencial'
                st.session_state.ponteiro += 1
                st.rerun()
        with col2:
            if st.button("🟥 SAIR", use_container_width=True):
                st.session_state.dados.at[p, 'Status'] = 'Descartado'
                st.session_state.ponteiro += 1
                st.rerun()
        with col3:
            if st.button("⏭️", use_container_width=True):
                st.session_state.ponteiro += 1
                st.rerun()
    else:
        st.success("Lista Concluída!")
        if st.button("Reiniciar"):
            st.session_state.ponteiro = 0; st.rerun()

    # 3. Exportação Completa
    st.divider()
    st.subheader("📥 Exportar Resultado")
    formato = st.radio("Escolha o formato:", ["Excel", "PDF"], horizontal=True)

    if st.button("💾 Gerar Arquivo Final"):
        if formato == "Excel":
            output = BytesIO()
            df.to_excel(output, index=False)
            st.download_button("Baixar Excel", output.getvalue(), "leads_final.xlsx")
        else:
            # Geração de PDF nativa e sem bugs
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", "B", 14)
            pdf.cell(0, 10, "Relatorio de Leads Processados", ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("helvetica", size=10)
            for i, row in df.iterrows():
                # Define a cor do texto no PDF com base no status
                if row['Status'] == 'Potencial':
                    pdf.set_text_color(0, 128, 0) # Verde
                elif row['Status'] == 'Descartado':
                    pdf.set_text_color(255, 0, 0) # Vermelho
                else:
                    pdf.set_text_color(0, 0, 0) # Preto
                
                info_texto = row.get('Informação', row.get('Nome', 'Sem dados'))
                texto_linha = f"#{i+1} [{row['Status']}] - {info_texto}"
                
                # Multi_cell evita que o texto longo saia da página
                pdf.multi_cell(0, 8, texto_linha, border=1)
                pdf.ln(2)
            
            pdf_bytes = pdf.output()
            st.download_button("Baixar PDF", bytes(pdf_bytes), "leads_final.pdf")
