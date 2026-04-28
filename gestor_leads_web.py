import streamlit as st
import pandas as pd
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from fpdf import FPDF
from io import BytesIO
import re

st.set_page_config(page_title="Gestor de Leads", layout="centered")
st.title("Gestor de Leads")

# Função que lê a linha inteira e calcula a distância em pixels
def extrair_linhas_espacadas(imagem):
    # Tratamento pesado para contraste
    imagem = ImageOps.grayscale(imagem)
    imagem = imagem.filter(ImageFilter.SHARPEN)
    
    # Pegamos os dados detalhados do OCR (inclui posição X, Y e largura)
    dados_ocr = pytesseract.image_to_data(imagem, lang='por', output_type=pytesseract.Output.DICT)
    
    n_boxes = len(dados_ocr['text'])
    linhas_agrupadas = {}

    for i in range(n_boxes):
        confianca = int(dados_ocr['conf'][i])
        texto = dados_ocr['text'][i].strip()
        
        # Só processa se a IA tiver certeza do que leu e se não for vazio
        if confianca > 30 and texto:
            top = dados_ocr['top'][i]
            left = dados_ocr['left'][i]
            width = dados_ocr['width'][i]
            
            # Agrupa palavras que estão na mesma altura (margem de 15 pixels)
            y_linha = top // 15 
            
            if y_linha not in linhas_agrupadas:
                linhas_agrupadas[y_linha] = []
                
            linhas_agrupadas[y_linha].append({
                'texto': texto,
                'left': left,
                'right': left + width
            })

    lista_final = []
    
    # Processa cada linha horizontal encontrada
    for y in sorted(linhas_agrupadas.keys()):
        palavras_da_linha = linhas_agrupadas[y]
        # Ordena as palavras da esquerda para a direita
        palavras_da_linha.sort(key=lambda k: k['left'])
        
        linha_construida = ""
        
        for idx in range(len(palavras_da_linha)):
            palavra_atual = palavras_da_linha[idx]
            linha_construida += palavra_atual['texto']
            
            # Se não for a última palavra, calcula a distância para a próxima
            if idx < len(palavras_da_linha) - 1:
                proxima_palavra = palavras_da_linha[idx + 1]
                distancia_pixels = proxima_palavra['left'] - palavra_atual['right']
                
                # SE A DISTÂNCIA FOR MAIOR QUE 50 PIXELS, COLOCA UM ESPAÇO GRANDE
                if distancia_pixels > 50:
                    linha_construida += "   |   " # Marcador visual de coluna
                else:
                    linha_construida += " "
                    
        if len(linha_construida.strip()) > 5:
            lista_final.append({
                "Informação": linha_construida.strip(),
                "Status": "Pendente"
            })
            
    return pd.DataFrame(lista_final)

# 1. Upload
arquivo = st.file_uploader("Carregar Foto ou Planilha", type=["xlsx", "csv", "jpg", "png", "jpeg"])

if arquivo:
    if "dados" not in st.session_state:
        if arquivo.type in ["image/jpeg", "image/png"]:
            with st.spinner("Analisando distâncias e lendo linhas..."):
                img = Image.open(arquivo)
                df_extraido = extrair_linhas_espacadas(img)
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
            info_atual = contato.get('Informação', contato.get('Nome', 'Sem dados'))
            st.write(f"📄 **Dados da Linha:** {info_atual}")
            
            # Busca sequências numéricas para ativar os botões
            numeros_isolados = "".join(re.findall(r'\d+', str(info_atual)))
            
            if len(numeros_isolados) >= 8:
                st.success(f"📞 Número Detectado: {numeros_isolados}")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'''<a href="tel:{numeros_isolados}" style="text-decoration:none;">
                        <button style="width:100%; border-radius:10px; background-color:#25D366; color:white; border:none; padding:12px; font-weight:bold;">
                        📞 Ligar</button></a>''', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'''<a href="https://wa.me{numeros_isolados}" target="_blank" style="text-decoration:none;">
                        <button style="width:100%; border-radius:10px; background-color:#128C7E; color:white; border:none; padding:12px; font-weight:bold;">
                        💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            else:
                st.warning("⚠️ O leitor não identificou uma sequência numérica válida para discagem nesta linha.")

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

    # 3. Exportação
    st.divider()
    st.subheader("📥 Exportar Resultado")
    formato = st.radio("Escolha o formato:", ["Excel", "PDF"], horizontal=True)

    if st.button("💾 Gerar Arquivo Final"):
        if formato == "Excel":
            output = BytesIO()
            df.to_excel(output, index=False)
            st.download_button("Baixar Excel", output.getvalue(), "leads_final.xlsx")
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
            
            pdf_bytes = pdf.output()
            st.download_button("Baixar PDF", bytes(pdf_bytes), "leads_final.pdf")
