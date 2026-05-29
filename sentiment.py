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

    # MIGRACAO FORÇADA: Verifica e adiciona colunas necessárias dinamicamente
    cursor.execute("PRAGMA table_info(comentarios)")
    colunas = [col[1] for col in cursor.fetchall()]

    if 'data' not in colunas:
        try:
            cursor.execute('ALTER TABLE comentarios ADD COLUMN data TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except sqlite3.OperationalError:
            pass

    if 'categoria' not in colunas:
        try:
            cursor.execute('ALTER TABLE comentarios ADD COLUMN categoria TEXT DEFAULT "Geral"')
        except sqlite3.OperationalError:
            pass

    if 'nota' not in colunas:
        try:
            cursor.execute('ALTER TABLE comentarios ADD COLUMN nota INTEGER DEFAULT 5')
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


def salvar_comentario(usuario, comentario, sentimento, categoria, nota):
    conexao = sqlite3.connect('banco1.db')
    cursor = conexao.cursor()
    cursor.execute("PRAGMA table_info(comentarios)")
    colunas = [col[1] for col in cursor.fetchall()]

    campos = ["usuario", "comentario", "sentimento"]
    valores = [usuario, comentario, sentimento]
    placeholders = ["?", "?", "?"]

    if 'categoria' in colunas:
        campos.append("categoria")
        valores.append(categoria)
        placeholders.append("?")
    if 'nota' in colunas:
        campos.append("nota")
        valores.append(nota)
        placeholders.append("?")

    query = f"INSERT INTO comentarios ({', '.join(campos)}) VALUES ({', '.join(placeholders)})"
    cursor.execute(query, valores)
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
    cursor.execute("PRAGMA table_info(comentarios)")
    colunas = [col[1] for col in cursor.fetchall()]

    colunas_select = ["id", "usuario", "comentario", "sentimento"]

    if 'categoria' in colunas:
        colunas_select.append("categoria")
    else:
        colunas_select.append("'Geral' as categoria")

    if 'nota' in colunas:
        colunas_select.append("nota")
    else:
        colunas_select.append("5 as nota")

    if 'data' in colunas:
        colunas_select.append("data")
        query = f"SELECT {', '.join(colunas_select)} FROM comentarios ORDER BY data DESC"
    else:
        colunas_select.append("NULL as data")
        query = f"SELECT {', '.join(colunas_select)} FROM comentarios"

    cursor.execute(query)
    dados = cursor.fetchall()
    conexao.close()
    return dados


def consultar_comentarios_por_usuario(usuario):
    conexao = sqlite3.connect('banco1.db')
    cursor = conexao.cursor()
    cursor.execute("PRAGMA table_info(comentarios)")
    colunas = [col[1] for col in cursor.fetchall()]

    colunas_select = ["id", "usuario", "comentario", "sentimento"]

    if 'categoria' in colunas:
        colunas_select.append("categoria")
    else:
        colunas_select.append("'Geral' as categoria")

    if 'nota' in colunas:
        colunas_select.append("nota")
    else:
        colunas_select.append("5 as nota")

    if 'data' in colunas:
        colunas_select.append("data")
        query = f"SELECT {', '.join(colunas_select)} FROM comentarios WHERE usuario = ? ORDER BY data DESC"
    else:
        colunas_select.append("NULL as data")
        query = f"SELECT {', '.join(colunas_select)} FROM comentarios WHERE usuario = ?"

    cursor.execute(query, (usuario,))
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

# Lista padronizada de categorias com os novos tópicos incluídos
CATEGORIAS_DISPONIVEIS = [
    "Ambiente Acadêmico",
    "Tecnologias",
    "Mercado de Trabalho e Carreira",
    "Atividades Complementares",
    "Infraestrutura",
    "Corpo Docente",
    "Administração",
    "Ementa",
    "Outro"
]

# 🔎 LÓGICA DE SESSÃO 🔎 #
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("Portal de Satisfação do Aluno")
    aba = st.sidebar.selectbox("Navegação:", ["Login", "Cadastro"])
    tipo_perfil = st.radio("Entrar como:", ["Usuário", "Administrador"], horizontal=True)

    if aba == "Cadastro":
        with st.container():
            st.subheader(f"Novo Registro - {tipo_perfil}")
            nome = st.text_input("Nome Completo")
            email = st.text_input("E-mail")
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
                senha = st.text_input("Chave de Acesso de Administrador.", type="password")
                if st.form_submit_button("Acessar"):
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

    if st.session_state.tipo_usuario == "Administrador":
        menu_options = ["Dashboard de Inteligência", "Sair"]
    else:
        menu_options = ["Feedback", "Meus Comentários", "Sair"]

    escolha = st.sidebar.radio("Ir para:", menu_options)

    if escolha == "Feedback":
        st.header("📝 Sua opinião vale muito")

        # Seleção de Categorias Atualizadas
        categoria_selecionada = st.selectbox(
            "Selecione o tópico do seu feedback:",
            CATEGORIAS_DISPONIVEIS
        )

        # Avaliação por estrelas de 1 a 5
        st.write("Dê uma nota para esta categoria:")
        nota_estrelas = st.feedback("stars")
        nota_final = (nota_estrelas + 1) if nota_estrelas is not None else 5

        feedback = st.text_area("Descreva como foi sua experiência com esse tópico:",
                                placeholder="Escreva aqui...")
        if st.button("Enviar Avaliação"):
            if feedback:
                with st.spinner("Recebendo comentário..."):
                    en_text = traduzir_para_ingles(feedback)
                    score = SentimentIntensityAnalyzer().polarity_scores(en_text)

                    # Definição técnica interna do sentimento
                    sent = "Neutro"
                    if score["compound"] >= 0.05:
                        sent = "Positivo"
                    elif score["compound"] <= -0.05:
                        sent = "Negativo"

                    # Grava os dados completos no banco (mantendo a inteligência para os painéis)
                    atualizar_sentimento(sent)
                    salvar_comentario(st.session_state.nome_usuario, feedback, sent, categoria_selecionada, nota_final)

                    # Lógica de interface com mensagens discretas solicitadas (sem expor o rótulo do algoritmo)
                    if sent == "Positivo":
                        st.balloons()
                        st.success("Obrigado pelo feedback! Vamos continuar trabalhando para manter a qualidade.")
                    elif sent == "Negativo":
                        st.warning("Obrigado pelo feedback! Vamos trabalhar para melhorar isso.")
                    else:
                        st.info("Obrigado pelo feedback! Levaremos estes pontos em consideração.")

    elif escolha == "Meus Comentários":
        st.header("👤 Meu Histórico de Feedbacks")
        st.caption("Aqui você pode revisar e excluir os feedbacks enviados por você.")

        meus_dados = consultar_comentarios_por_usuario(st.session_state.nome_usuario)

        if meus_dados:
            df_meus = pd.DataFrame(meus_dados,
                                   columns=['ID', 'Usuário', 'Texto', 'Sentimento', 'Categoria', 'Nota', 'Data'])

            # Formatação visual das estrelas na exibição da tabela
            df_exibicao = df_meus.copy()
            df_exibicao['Nota'] = df_exibicao['Nota'].apply(lambda n: '★' * int(n))

            st.dataframe(df_exibicao[['ID', 'Categoria', 'Texto', 'Sentimento', 'Nota', 'Data']],
                         use_container_width=True)

            st.divider()
            st.subheader("🗑 Apagar um Comentário")

            ids_disponiveis = df_meus['ID'].tolist()
            id_para_excluir = st.selectbox("Selecione o ID do comentário que deseja remover permanentemente:",
                                           ids_disponiveis)

            if st.button("Confirmar Exclusão"):
                excluir_comentario(id_para_excluir)
                st.success("Comentário removido com sucesso!")
                st.rerun()
        else:
            st.info("Você ainda não enviou nenhum feedback para a nossa plataforma.")

    elif escolha == "Dashboard de Inteligência":
        st.header("📊 Painel de Business Intelligence")

        # --- BUSCA DE DADOS ---
        dados_sent = consultar_sentimentos()
        comentarios_raw = consultar_comentarios()
        df_coments = pd.DataFrame(comentarios_raw,
                                  columns=['ID', 'Usuário', 'Texto', 'Sentimento', 'Categoria', 'Nota', 'Data'])

        # --- MÉTRICAS (KPIs) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Feedbacks", len(df_coments))
        if not df_coments.empty:
            pos_pct = len(df_coments[df_coments['Sentimento'] == 'Positivo']) / len(df_coments) * 100
            col2.metric("Índice de Aprovação", f"{pos_pct:.1f}%")
            media_geral = df_coments['Nota'].mean()
            col3.metric("Média de Avaliação Geral", f"{media_geral:.2f} ★")
            col4.metric("Status do Sistema", "Ativo")

        # --- GRÁFICOS ---
        tab1, tab2, tab3 = st.tabs(
            ["Distribuição & Médias", "Nuvem de Palavras", "Gestão de Dados & Filtros por Categoria"])

        with tab1:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("Distribuição Geral de Sentimentos")
                if dados_sent:
                    df_grafico = pd.DataFrame(dados_sent, columns=['Sentimento', 'Quantidade'])
                    st.bar_chart(df_grafico.set_index('Sentimento'))
                else:
                    st.info("Sem dados de sentimentos agregados.")
            with col_g2:
                st.subheader("Média de Estrelas por Tópico")
                if not df_coments.empty:
                    df_medias = df_coments.groupby('Categoria')['Nota'].mean().reset_index()
                    st.bar_chart(df_medias.set_index('Categoria'))
                else:
                    st.info("Aguardando avaliações para calcular as médias por tópico.")

        with tab2:
            if not df_coments.empty:
                st.subheader("Nuvem de Termos Mais Frequentes")
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
            st.subheader("Filtros Avançados e Consulta de Dados")

            # FILTRO POR CATEGORIAS SOLICITADO #
            categorias_existentes = df_coments[
                'Categoria'].unique().tolist() if not df_coments.empty else CATEGORIAS_DISPONIVEIS
            filtro_categoria = st.multiselect(
                "Filtrar comentários por Categoria/Tópico:",
                options=categorias_existentes,
                default=categorias_existentes
            )

            filtro_sent = st.multiselect(
                "Filtrar por Sentimento:",
                ["Positivo", "Neutro", "Negativo"],
                default=["Positivo", "Neutro", "Negativo"]
            )

            busca = st.text_input("🔍 Buscar termo específico no texto do comentário")

            # Aplicação dos Filtros no DataFrame do Admin
            df_filtrado = df_coments.copy()
            if not df_filtrado.empty:
                df_filtrado = df_filtrado[
                    (df_filtrado['Categoria'].isin(filtro_categoria)) &
                    (df_filtrado['Sentimento'].isin(filtro_sent))
                    ]
                if busca:
                    df_filtrado = df_filtrado[df_filtrado['Texto'].str.contains(busca, case=False)]

            # Formata a exibição das notas como estrelas na visualização de dados
            df_filtrado_exibir = df_filtrado.copy()
            if not df_filtrado_exibir.empty:
                df_filtrado_exibir['Nota'] = df_filtrado_exibir['Nota'].apply(lambda n: '★' * int(n))

            st.dataframe(df_filtrado_exibir, use_container_width=True)

            # Exportação CSV dos dados filtrados
            if not df_filtrado.empty:
                csv = df_filtrado.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Relatório Filtrado (CSV)", data=csv,
                                   file_name="relatorio_satisfacao_filtrado.csv",
                                   mime="text/csv")

            # Exclusão administrativa total
            st.divider()
            id_exc = st.number_input("ID administrativo para excluir permanentemente:", step=1, value=0)
            if st.button("🗑 Confirmar Exclusão Administrativa"):
                excluir_comentario(id_exc)
                st.success("Registro excluído!")
                st.rerun()

    elif escolha == "Sair":
        st.session_state.logado = False
        st.rerun()