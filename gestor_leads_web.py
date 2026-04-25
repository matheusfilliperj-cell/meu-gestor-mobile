import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF
import os

st.set_page_config(page_title="Gestor Leads Mobile", layout="centered")

st.title("📱 Gestor de Leads Mobile")
st.markdown("### Seleção e Ação Rápida")

# 1. Carregamento do Arquivo
arquivo = st.file_uploader("Carregar Lista (Excel/CSV)", type=["xlsx", "csv"])

if arquivo:
    if "dados" not in st.session_state:
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
        st.info(f"Contato {p + 1} de {len(df)}")
        contato = df.iloc[p]
        
        # Card Visual para Celular
        with st.container(border=True):
            nome_completo = f"{contato.get('Nome', 'N/A')} {contato.get('Sobrenome', '')}"
            st.subheader(nome_completo)
            
            # Limpeza do número para o link de ligação/zap
            tel_bruto = str(contato.get('Telefone', ''))
            tel_limpo = "".join(filter(str.isdigit, tel_bruto))
            
            st.write(f"**Telefone:** {tel_bruto}")

            # Botões de Ação Direta
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f'''<a href="tel:{tel_limpo}" style="text-decoration:none;">
                    <button style="width:100%; border-radius:10px; background-color:#25D366; color:white; border:none; padding:12px; font-weight:bold;">
                    📞 Ligar</button></a>''', unsafe_allow_html=True)
            with col_b:
                # Se for Rio de Janeiro, o link já vai com 5521...
                st.markdown(f'''<a href="https://wa.me{tel_limpo}" target="_blank" style="text-decoration:none;">
                    <button style="width:100%; border-radius:10px; background-color:#128C7E; color:white; border:none; padding:12px; font-weight:bold;">
                    💬 WhatsApp</button></a>''', unsafe_allow_html=True)

        st.divider()
        
        # Decisões de Status
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
            if st.button("⏭️ PULAR", use_container_width=True):
                st.session_state.ponteiro += 1
                st.rerun()
    else:
        st.success("🏁 Lista Concluída!")
        if st.button("Recomeçar"):
            st.session_state.ponteiro = 0
            st.rerun()

    # 3. Exportação (Usando fpdf2 para evitar erros na nuvem)
    st.divider()
    st.subheader("📥 Exportar Resultado")
    formato = st.radio("Formato:", ["Excel", "PDF"], horizontal=True)

    if st.button("Gerar Arquivo Final"):
        if formato == "Excel":
            output = BytesIO()
            # Estilo simples para Excel (Cores)
            def aplicar_cor(row):
                if row['Status'] == 'Potencial': return ['background-color: #90EE90'] * len(row)
                if row['Status'] == 'Descartado': return ['background-color: #FF7F7F'] * len(row)
                return [''] * len(row)
            
            df.style.apply(aplicar_cor, axis=1).to_excel(output, index=False)
            st.download_button("Baixar Excel", output.getvalue(), "leads_mobile.xlsx")
        
        else:
            # Geração de PDF com fpdf2
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", "B", 14)
            pdf.cell(0, 10, "Relatorio de Leads - Gestor Mobile", ln=True, align='C')
            pdf.set_font("helvetica", size=10)
            pdf.ln(10)
            
            for i, row in df.iterrows():
                texto_linha = f"[{row['Status']}] {row.get('Nome','')} {row.get('Sobrenome','')} - {row.get('Telefone','')}"
                # Cor do texto baseada no status
                if row['Status'] == 'Potencial': pdf.set_text_color(0, 128, 0) # Verde
                elif row['Status'] == 'Descartado': pdf.set_text_color(255, 0, 0) # Vermelho
                else: pdf.set_text_color(0, 0, 0)
                
                pdf.cell(0, 8, texto_linha, ln=True)
            
            pdf_bytes = pdf.output()
            st.download_button("Baixar PDF", bytes(pdf_bytes), "leads_mobile.pdf")

# Prévia no rodapé
if arquivo:
    with st.expander("Ver lista completa"):
        st.dataframe(df)

