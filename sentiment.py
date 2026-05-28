# -*- coding: utf-8 -*-
# 🎀 Sistema de Satisfação do Cliente - Versão TCC Avançada 🎀 #

import streamlit as st
import sqlite3
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from googletrans import Translator
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io

# Configuração da página para um visual mais profissional
st.set_page_config(page_title="Analytics de Satisfação", layout="wide")

# Instalação de recursos necessários
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except:
    nltk.download("vader_lexicon")


# 📩 FUNÇÃO PARA TRADUÇÃO 📩 #
def traduzir_para_ingles(texto):
    tradutor = Translator()
    try:
        traducao = tradutor.translate(texto, src='pt', dest='en')
        return traducao.text
    except:
        return texto


# 🎲 BANCO DE DADOS 🎲 #
def criar_tabelas():
    conexao = sqlite3.connect('banco1.db')
    cursor = conexao.cursor()

    # Tabela de Cadastro
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cadastro (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nome TEXT, email TEXT, senha TEXT, tipo TEXT
        )
    ''')
    try:
        cursor.execute('ALTER TABLE cadastro ADD COLUMN tipo TEXT')
    except sqlite3.OperationalError:
        pass

    # Tabela de Sentimentos Agregados
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS analise_sentimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, sentimento TEXT, quantidade INTEGER)')

    # Tabela de Comentários (Garante a criação base)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            usuario TEXT, 
            comentario TEXT, 
            sentimento TEXT
        )
    ''')

    # MIGRACAO FORÇADA: Verifica se a coluna 'data' existe antes de tentar selecionar
    cursor.execute("PRAGMA table_info(comentarios)")
    colunas = [col[1] for col in cursor.fetchall()]

    if 'data' not in colunas:
        try:
            cursor.execute('ALTER TABLE comentarios ADD COLUMN data TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except sqlite3.OperationalError:
            pass

    conexao.commit()
    conexao.close()


def cadastrar_usuario(nome, email, senha, tipo):
    if tipo == "Administrador" and senha != "1234":
        return "SENHA_ADMIN_INVALIDA"
    conexao = sqlite3.connect('banco1.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT * FROM cadastro WHERE email = ?', (email,))
    if cursor.fetchone():
        conexao.close()
        return "EMAIL_EXISTENTE"
    cursor.execute('INSERT INTO cadastro (nome, email, senha, tipo) VALUES (?, ?, ?, ?)', (nome, email, senha, tipo))
    conexao.commit()
    conexao.close()
    return "SUCESSO"


def login_usuario(email, senha, tipo):
    conexao = sqlite3.connect('banco1.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT nome, tipo FROM cadastro WHERE email = ? AND senha = ? AND tipo = ?', (email, senha, tipo))
    resultado = cursor.fetchone()
    conexao.close()
    return resultado


def atualizar_sentimento(sentimento):
    conexao = sqlite3.connect('banco1.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT quantidade FROM analise_sentimentos WHERE sentimento = ?', (sentimento,))
    resultado = cursor.fetchone()
    if resultado:
        cursor.execute('UPDATE analise_sentimentos SET quantidade = ? WHERE sentimento = ?',
                       (resultado[0] + 1, sentimento))
    else:
        cursor.execute('INSERT INTO analise_sentimentos (sentimento, quantidade) VALUES (?, ?)', (sentimento, 1))
    conexao.commit()
    conexao.close()


def salvar_comentario(usuario, comentario, sentimento):
    conexao = sqlite3.connect('banco1.db')
    cursor = conexao.cursor()
    cursor.execute('INSERT INTO comentarios (usuario, comentario, sentimento) VALUES (?, ?, ?)',
                   (usuario, comentario, sentimento))
    conexao.commit()
    conexao.close()


def consultar_sentimentos():
    conexao = sqlite3.connect('banco1.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT sentimento, quantidade FROM analise_sentimentos')
    dados = cursor.fetchall()
    conexao.close()
    return dados


def consultar_comentarios():
    conexao = sqlite3.connect('banco1.db')
    cursor = conexao.cursor()
    # Verifica novamente a existência da coluna para evitar erro em tempo de execução
    cursor.execute("PRAGMA table_info(comentarios)")
    colunas = [col[1] for col in cursor.fetchall()]

    if 'data' in colunas:
        cursor.execute('SELECT id, usuario, comentario, sentimento, data FROM comentarios ORDER BY data DESC')
    else:
        cursor.execute('SELECT id, usuario, comentario, sentimento, NULL as data FROM comentarios')

    dados = cursor.fetchall()
    conexao.close()
    return dados


def excluir_comentario(id_coment):
    conexao = sqlite3.connect('banco1.db')
    cursor = conexao.cursor()
    cursor.execute('DELETE FROM comentarios WHERE id = ?', (id_coment,))
    conexao.commit()
    conexao.close()


# Iniciar banco e aplicar migrações
criar_tabelas()

# 🔎 LÓGICA DE SESSÃO 🔎 #
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🛡️ Portal de Satisfação do Cliente")
    aba = st.sidebar.selectbox("Navegação:", ["Login", "Cadastro"])
    tipo_perfil = st.radio("Entrar como:", ["Usuário", "Administrador"], horizontal=True)

    if aba == "Cadastro":
        with st.container():
            st.subheader(f"Novo Registro - {tipo_perfil}")
            nome = st.text_input("Nome Completo")
            email = st.text_input("E-mail Institucional")
            senha = st.text_input("Senha", type="password")
            if st.button("Finalizar Cadastro"):
                res = cadastrar_usuario(nome, email, senha, tipo_perfil)
                if res == "SUCESSO":
                    st.success("Conta criada!")
                elif res == "SENHA_ADMIN_INVALIDA":
                    st.error("Chave Admin incorreta.")
                else:
                    st.error("E-mail já em uso.")
    else:
        with st.form("login_form"):
            st.subheader(f"Login {tipo_perfil}")
            if tipo_perfil == "Administrador":
                senha = st.text_input("Chave de Acesso (1234)", type="password")
                if st.form_submit_button("Acessar Analytics"):
                    if senha == "1234":
                        st.session_state.logado, st.session_state.nome_usuario, st.session_state.tipo_usuario = True, "Admin", "Administrador"
                        st.rerun()
                    else:
                        st.error("Senha inválida.")
            else:
                email = st.text_input("E-mail")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    u = login_usuario(email, senha, tipo_perfil)
                    if u:
                        st.session_state.logado, st.session_state.nome_usuario, st.session_state.tipo_usuario = True, u[
                            0], u[1]
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")

else:
    # --- ÁREA LOGADA ---
    st.sidebar.title(f"👤 {st.session_state.nome_usuario}")
    st.sidebar.caption(f"Perfil: {st.session_state.tipo_usuario}")

    menu_options = ["Feedback"]
    if st.session_state.tipo_usuario == "Administrador":
        menu_options.append("Dashboard de Inteligência")
    menu_options.append("Sair")

    escolha = st.sidebar.radio("Ir para:", menu_options)

    if escolha == "Feedback":
        st.header("📝 Sua opinião vale muito")
        feedback = st.text_area("Descreva como foi sua experiência conosco:", placeholder="Escreva aqui...")
        if st.button("Enviar Avaliação"):
            if feedback:
                with st.spinner("Analisando sentimento..."):
                    en_text = traduzir_para_ingles(feedback)
                    score = SentimentIntensityAnalyzer().polarity_scores(en_text)
                    sent = "Neutro"
                    if score["compound"] >= 0.05:
                        sent = "Positivo"
                    elif score["compound"] <= -0.05:
                        sent = "Negativo"

                    atualizar_sentimento(sent)
                    salvar_comentario(st.session_state.nome_usuario, feedback, sent)

                    if sent == "Positivo": st.balloons()
                    st.success(f"Obrigado! Identificamos que seu feedback é {sent}.")

    elif escolha == "Dashboard de Inteligência":
        st.header("📊 Painel de Business Intelligence")

        # --- BUSCA DE DADOS ---
        dados_sent = consultar_sentimentos()
        comentarios_raw = consultar_comentarios()
        df_coments = pd.DataFrame(comentarios_raw, columns=['ID', 'Usuário', 'Texto', 'Sentimento', 'Data'])

        # --- MÉTRICAS (KPIs) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Feedbacks", len(df_coments))
        if not df_coments.empty:
            pos_pct = len(df_coments[df_coments['Sentimento'] == 'Positivo']) / len(df_coments) * 100
            col2.metric("Índice de Aprovação", f"{pos_pct:.1f}%")
            col3.metric("Último Sentimento", df_coments['Sentimento'].iloc[0])
        col4.metric("Status do Sistema", "Ativo")

        # --- GRÁFICOS ---
        tab1, tab2, tab3 = st.tabs(["Distribuição", "Nuvem de Palavras", "Gestão de Dados"])

        with tab1:
            if dados_sent:
                df_grafico = pd.DataFrame(dados_sent, columns=['Sentimento', 'Quantidade'])
                st.bar_chart(df_grafico.set_index('Sentimento'))
            else:
                st.info("Sem dados suficientes.")

        with tab2:
            if not df_coments.empty:
                texto_geral = " ".join(df_coments['Texto'])
                wordcloud = WordCloud(width=800, height=400, background_color='white', colormap='viridis').generate(
                    texto_geral)
                fig, ax = plt.subplots()
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis("off")
                st.pyplot(fig)
            else:
                st.info("Aguardando feedbacks para gerar nuvem.")

        with tab3:
            st.subheader("Filtros Avançados")
            busca = st.text_input("🔍 Buscar termo no comentário")
            filtro_sent = st.multiselect("Filtrar por Sentimento", ["Positivo", "Neutro", "Negativo"],
                                         default=["Positivo", "Neutro", "Negativo"])

            df_filtrado = df_coments[df_coments['Sentimento'].isin(filtro_sent)]
            if busca:
                df_filtrado = df_filtrado[df_filtrado['Texto'].str.contains(busca, case=False)]

            st.dataframe(df_filtrado, use_container_width=True)

            # Exportação CSV
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Relatório (CSV)", data=csv, file_name="relatorio_satisfacao.csv",
                               mime="text/csv")

            # Exclusão
            st.divider()
            id_exc = st.number_input("ID para excluir", step=1, value=0)
            if st.button("🗑️ Excluir permanentemente"):
                excluir_comentario(id_exc)
                st.rerun()

    elif escolha == "Sair":
        st.session_state.logado = False
        st.rerun()