import io
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo  # Fuso horário nativo no Python 3.9+
import pandas as pd
import requests
import streamlit as st

st.set_page_config(layout="wide", page_title="GESTÃO DE ATENDIMENTOS DO DIA")

URL_APP_SCRIPT = "https://script.google.com/macros/s/AKfycbyB5a77mt3IBHeE23f9dBXHqkNCr6F_y7ZmSYsLaUjW9Y9Tt5twou11VAomrb_r_b9_8w/exec"
FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


# HELPER PARA OTER DATA E HORA DE BRASÍLIA
def obter_agora_brasilia():
    return datetime.now(FUSO_BRASILIA)


def obter_hoje_brasilia():
    return obter_agora_brasilia().date()


# FUNÇÕES DE INTEGRAÇÃO COM O GOOGLE APPS SCRIPT
def carregar_dados():
    try:
        res = requests.get(URL_APP_SCRIPT, allow_redirects=True, timeout=10)
        if res.status_code == 200 and "application/json" in res.headers.get(
            "Content-Type", ""
        ):
            dados = res.json()
            pacientes = []
            for row in dados:
                dt_reg = row.get("data_registro", "")
                if isinstance(dt_reg, str) and dt_reg:
                    try:
                        dt_obj = datetime.strptime(
                            dt_reg[:10], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        dt_obj = obter_hoje_brasilia()
                else:
                    dt_obj = obter_hoje_brasilia()

                pacientes.append({
                    "id": int(row.get("id", 0)),
                    "data_registro": dt_obj,
                    "Horário de Chegada": str(
                        row.get("Horário de Chegada", "")
                    ).upper(),
                    "Nome": str(row.get("Nome", "")).upper(),
                    "CPF": str(row.get("CPF", "")).upper(),
                    "Data de Nascimento": str(
                        row.get("Data de Nascimento", "")
                    ).upper(),
                    "Atendimento": str(row.get("Atendimento", "")).upper(),
                    "Profissional": str(
                        row.get("Profissional", "NÃO INFORMADO")
                    ).upper(),
                    "Observações": str(row.get("Observações", "")).upper(),
                    "Status": str(row.get("Status", "AGUARDANDO")).upper(),
                })
            return pacientes
        else:
            st.error(
                "NÃO FOI POSSÍVEL LER OS DADOS DA PLANILHA. VERIFIQUE AS"
                " PERMISSÕES DO APPS SCRIPT ('QUALQUER PESSOA')."
            )
            return []
    except Exception as e:
        st.error(f"ERRO DE CONEXÃO: {e}")
        return []


def salvar_todos_dados(lista_pacientes):
    dados_preparados = []
    for p in lista_pacientes:
        p_copia = p.copy()
        if isinstance(p_copia["data_registro"], date):
            p_copia["data_registro"] = p_copia["data_registro"].strftime(
                "%Y-%m-%d"
            )
        dados_preparados.append(p_copia)

    try:
        res = requests.post(
            URL_APP_SCRIPT, json=dados_preparados, allow_redirects=True
        )
        if res.status_code == 200:
            return True
        else:
            st.error(f"ERRO AO SALVAR NA PLANILHA: STATUS {res.status_code}")
            return False
    except Exception as e:
        st.error(f"ERRO AO ENVIAR DADOS: {e}")
        return False


# INICIALIZAÇÃO DE ESTADOS
if "pacientes" not in st.session_state:
    st.session_state.pacientes = carregar_dados()

if "paciente_selecionado_id" not in st.session_state:
    st.session_state.paciente_selecionado_id = None

if "modo_edicao_concluido" not in st.session_state:
    st.session_state.modo_edicao_concluido = False

if "form_id" not in st.session_state:
    st.session_state.form_id = 0

PROFISSIONAIS_LISTA = [
    "ALYSSON",
    "A.CRISTINA DIAS",
    "CRISTINA",
    "DEBORA BITENCORTE",
    "DEBORA CRISTIANE",
    "DIOLINA",
    "ERIKA=",
    "GIZELE",
    "GLEICE",
    "JOSIANE",
    "KAROLINY",
    "MARCOS",
    "MARIA JOSE PEREIRA DA COSTA",
    "MICHELLE",
]


def formatar_cpf(texto_cpf):
    numeros = re.sub(r"\D", "", texto_cpf)
    if len(numeros) == 11:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
    return texto_cpf.strip().upper()


def obter_pacientes_hoje():
    hoje = obter_hoje_brasilia()
    return [
        p for p in st.session_state.pacientes if p.get("data_registro") == hoje
    ]


def gerar_rotulos_unicos(lista_nomes):
    contagem_primeiros_nomes = {}
    for nome in lista_nomes:
        primeiro_nome = nome.strip().split()[0]
        contagem_primeiros_nomes[primeiro_nome] = (
            contagem_primeiros_nomes.get(primeiro_nome, 0) + 1
        )

    mapeamento = {}
    for nome in lista_nomes:
        partes = nome.strip().split()
        primeiro_nome = partes[0]
        if contagem_primeiros_nomes[primeiro_nome] > 1:
            nome_exibicao = (
                " ".join(partes[:2]) if len(partes) > 1 else primeiro_nome
            )
        else:
            nome_exibicao = primeiro_nome
        mapeamento[nome] = nome_exibicao.upper()

    return mapeamento


OPCOES_ATENDIMENTO = [
    "SELECIONE...",
    "MEDICAÇÃO",
    "AFERIR PRESSÃO",
    "TESTE DE IST",
    "TESTE DE GRAVIDEZ",
    "TESTE DE COVID",
    "CURATIVO",
    "RETIRADA DE PONTOS",
]

MAPA_PROFISSIONAIS = gerar_rotulos_unicos(PROFISSIONAIS_LISTA)
OPCOES_PROFISSIONAIS_EXIBICAO = ["SELECIONE..."] + [
    MAPA_PROFISSIONAIS[p] for p in PROFISSIONAIS_LISTA
]

st.title("📋 ATENDIMENTOS SALA DE OBSERVAÇÃO")

if st.button("🔄 RECARREGAR DADOS DA PLANILHA"):
    st.session_state.pacientes = carregar_dados()
    st.success("DADOS ATUALIZADOS A PARTIR DO GOOGLE SHEETS!")
    st.rerun()

aba_cadastro, aba_equipe, aba_historico = st.tabs([
    "➕ CADASTRO DE PACIENTES",
    "👨‍⚕️ REGISTRO DO PROFISSIONAL & OBSERVAÇÕES",
    "📂 HISTÓRICO",
])


# ABA 1: CADASTRO E EDIÇÃO DIRETA
with aba_cadastro:
    st.header("NOVO CADASTRO")

    f_id = st.session_state.form_id

    atendimento_selecionado = st.selectbox(
        "ATENDIMENTO *",
        options=OPCOES_ATENDIMENTO,
        key=f"cad_atendimento_{f_id}",
    )

    nome_medicacao = ""
    if atendimento_selecionado.upper() == "MEDICAÇÃO":
        nome_medicacao = st.text_input(
            "QUAL A MEDICAÇÃO? *",
            placeholder="DIGITE O NOME E DOSAGEM (EX: DIPIRONA 500MG)",
            key=f"cad_medicacao_{f_id}",
        )

    with st.form("formulario_paciente", clear_on_submit=False):
        coluna1, coluna2 = st.columns(2)

        with coluna1:
            nome_paciente = st.text_input(
                "NOME COMPLETO *", key=f"cad_nome_{f_id}"
            )
            cpf = st.text_input(
                "CPF", placeholder="000.000.000-00", key=f"cad_cpf_{f_id}"
            )

        with coluna2:
            data_nascimento = st.date_input(
                "DATA DE NASCIMENTO",
                value=None,
                min_value=date(1900, 1, 1),
                max_value=obter_hoje_brasilia(),
                format="DD/MM/YYYY",
                key=f"cad_dt_nasc_{f_id}",
            )
            horario_chegada = st.time_input(
                "HORÁRIO DE CHEGADA",
                value=obter_agora_brasilia().time(),
                key=f"cad_horario_{f_id}",
            )

        botao_cadastrar = st.form_submit_button("SALVAR CADASTRO")

        if botao_cadastrar:
            numeros_cpf = re.sub(r"\D", "", cpf)

            if not nome_paciente.strip():
                st.error("O CAMPO 'NOME COMPLETO' É OBRIGATÓRIO.")
            elif not cpf.strip() and data_nascimento is None:
                st.error(
                    "É OBRIGATÓRIO PREENCHER PELO MENOS O CPF OU A DATA DE"
                    " NASCIMENTO."
                )
            elif cpf.strip() and len(numeros_cpf) != 11:
                st.error("O CPF DEVE CONTER EXATAMENTE 11 NÚMEROS.")
            elif atendimento_selecionado == "SELECIONE...":
                st.error("POR FAVOR, SELECIONE UM TIPO DE ATENDIMENTO.")
            elif (
                atendimento_selecionado.upper() == "MEDICAÇÃO"
                and not nome_medicacao.strip()
            ):
                st.error("POR FAVOR, INFORME O NOME DA MEDICAÇÃO.")
            else:
                cpf_formatado = (
                    formatar_cpf(cpf) if cpf.strip() else "NÃO INFORMADO"
                )
                data_nascimento_texto = (
                    data_nascimento.strftime("%d/%m/%Y")
                    if data_nascimento
                    else "NÃO INFORMADO"
                )
                atendimento_final = (
                    f"MEDICAÇÃO ({nome_medicacao.strip().upper()})"
                    if atendimento_selecionado.upper() == "MEDICAÇÃO"
                    else atendimento_selecionado.upper()
                )

                novo_registro = {
                    "id": max(
                        [p["id"] for p in st.session_state.pacientes], default=0
                    )
                    + 1,
                    "data_registro": obter_hoje_brasilia(),
                    "Horário de Chegada": horario_chegada.strftime("%H:%M"),
                    "Nome": nome_paciente.strip().upper(),
                    "CPF": cpf_formatado,
                    "Data de Nascimento": data_nascimento_texto,
                    "Atendimento": atendimento_final,
                    "Profissional": "NÃO INFORMADO",
                    "Observações": "",
                    "Status": "AGUARDANDO",
                }
                st.session_state.pacientes.append(novo_registro)

                if salvar_todos_dados(st.session_state.pacientes):
                    st.session_state.form_id += 1
                    st.success(
                        f"PACIENTE '{nome_paciente.strip().upper()}' CADASTRADO E"
                        " SALVO NA PLANILHA!"
                    )
                    st.rerun()

    st.divider()

    st.subheader("✏️ PACIENTES DO DIA")
    pacientes_hoje = obter_pacientes_hoje()

    if not pacientes_hoje:
        st.info("NENHUM PACIENTE CADASTRADO HOJE.")
    else:
        df_hoje = pd.DataFrame(pacientes_hoje)[
            [
                "id",
                "Horário de Chegada",
                "Nome",
                "CPF",
                "Data de Nascimento",
                "Atendimento",
                "Status",
            ]
        ]

        df_editado = st.data_editor(
            df_hoje,
            use_container_width=True,
            hide_index=True,
            disabled=["id", "Status"],
            column_config={
                "id": st.column_config.NumberColumn("ID"),
                "Horário de Chegada": st.column_config.TextColumn(
                    "HORÁRIO DE CHEGADA"
                ),
                "Nome": st.column_config.TextColumn("NOME COMPLETO"),
                "CPF": st.column_config.TextColumn("CPF"),
                "Data de Nascimento": st.column_config.TextColumn(
                    "DATA DE NASCIMENTO"
                ),
                "Atendimento": st.column_config.TextColumn("ATENDIMENTO"),
                "Status": st.column_config.TextColumn("STATUS"),
            },
            key="editor_tabela_cadastro",
        )

        if st.button("💾 SALVAR ALTERAÇÕES DA TABELA NA PLANILHA"):
            for row in df_editado.to_dict(orient="records"):
                for paciente_orig in st.session_state.pacientes:
                    if paciente_orig["id"] == row["id"]:
                        paciente_orig["Horário de Chegada"] = str(
                            row["Horário de Chegada"]
                        ).upper()
                        paciente_orig["Nome"] = str(row["Nome"]).upper()
                        paciente_orig["CPF"] = str(row["CPF"]).upper()
                        paciente_orig["Data de Nascimento"] = str(
                            row["Data de Nascimento"]
                        ).upper()
                        paciente_orig["Atendimento"] = str(
                            row["Atendimento"]
                        ).upper()

            if salvar_todos_dados(st.session_state.pacientes):
                st.success("ALTERAÇÕES SALVAS NA PLANILHA COM SUCESSO!")
                st.rerun()


# ABA 2: REGISTRO DO PROFISSIONAL
with aba_equipe:
    lista_pacientes_hoje = obter_pacientes_hoje()

    if not lista_pacientes_hoje:
        st.info("NÃO HÁ PACIENTES AGUARDANDO OU CADASTRADOS NO DIA DE HOJE.")
    else:
        paciente_atual = None
        if st.session_state.paciente_selecionado_id is not None:
            for p in lista_pacientes_hoje:
                if p["id"] == st.session_state.paciente_selecionado_id:
                    paciente_atual = p
                    break

        if paciente_atual is None and lista_pacientes_hoje:
            paciente_atual = lista_pacientes_hoje[0]
            st.session_state.paciente_selecionado_id = paciente_atual["id"]

        if paciente_atual:
            st.subheader(
                f"{str.upper(paciente_atual['Nome'])} —"
                f" {str.upper(paciente_atual['Atendimento'])}"
            )

            eh_concluido = paciente_atual.get("Status") == "CONCLUÍDO"
            bloquear_campos = (
                eh_concluido and not st.session_state.modo_edicao_concluido
            )

            if eh_concluido and bloquear_campos:
                st.warning(
                    "🔒 ESTE ATENDIMENTO JÁ FOI MARCADO COMO **CONCLUÍDO**. PARA"
                    " ALTERAR, SELECIONE O PACIENTE NO MENU SUSPENSO ABAIXO."
                )

            coluna_prof, coluna_obs = st.columns(2)

            with coluna_prof:
                prof_atual = paciente_atual.get("Profissional", "NÃO INFORMADO")
                rotulo_atual = MAPA_PROFISSIONAIS.get(
                    prof_atual, "SELECIONE..."
                )
                idx_prof = (
                    OPCOES_PROFISSIONAIS_EXIBICAO.index(rotulo_atual)
                    if rotulo_atual in OPCOES_PROFISSIONAIS_EXIBICAO
                    else 0
                )

                prof_selecionado_rotulo = st.selectbox(
                    "PROFISSIONAL RESPONSÁVEL / EXECUTOR",
                    options=OPCOES_PROFISSIONAIS_EXIBICAO,
                    index=idx_prof,
                    disabled=bloquear_campos,
                    key=f"prof_{paciente_atual['id']}",
                )

                opcoes_status = ["AGUARDANDO", "CONCLUÍDO"]
                status_atual_val = paciente_atual.get(
                    "Status", "AGUARDANDO"
                ).upper()
                indice_status = (
                    opcoes_status.index(status_atual_val)
                    if status_atual_val in opcoes_status
                    else 0
                )

                status_atendimento = st.selectbox(
                    "STATUS DO ATENDIMENTO",
                    options=opcoes_status,
                    index=indice_status,
                    disabled=bloquear_campos,
                    key=f"status_{paciente_atual['id']}",
                )

            with coluna_obs:
                texto_observacoes = st.text_area(
                    "OBSERVAÇÕES / CONDUTA",
                    value=paciente_atual["Observações"].upper(),
                    placeholder=(
                        "DIGITE AQUI AS OBSERVAÇÕES OU PROCEDIMENTOS"
                        " REALIZADOS..."
                    ),
                    disabled=bloquear_campos,
                    key=f"obs_{paciente_atual['id']}",
                )

            if not bloquear_campos:
                if st.button("SALVAR ATUALIZAÇÃO DE ATENDIMENTO"):
                    nome_prof_salvar = "NÃO INFORMADO"
                    if prof_selecionado_rotulo != "SELECIONE...":
                        for completo, rotulo in MAPA_PROFISSIONAIS.items():
                            if rotulo == prof_selecionado_rotulo:
                                nome_prof_salvar = completo.upper()
                                break

                    paciente_atual["Profissional"] = nome_prof_salvar
                    paciente_atual["Observações"] = (
                        texto_observacoes.strip().upper()
                    )
                    paciente_atual["Status"] = status_atendimento.upper()
                    st.session_state.modo_edicao_concluido = False

                    if salvar_todos_dados(st.session_state.pacientes):
                        st.success(
                            "INFORMAÇÕES ATUALIZADAS E SALVAS NA PLANILHA!"
                        )
                        st.rerun()

        st.divider()
        st.subheader("📋 RESUMO DOS ATENDIMENTOS DO DIA")

        tabela_resumo = pd.DataFrame(lista_pacientes_hoje)[
            [
                "id",
                "Horário de Chegada",
                "Nome",
                "CPF",
                "Data de Nascimento",
                "Atendimento",
                "Profissional",
                "Status",
                "Observações",
            ]
        ]

        evento_selecao = st.dataframe(
            tabela_resumo,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="tabela_equipe_selecao",
        )

        if evento_selecao and evento_selecao.get("selection", {}).get("rows"):
            linha_selecionada = evento_selecao["selection"]["rows"][0]
            paciente_clicado_id = tabela_resumo.iloc[linha_selecionada]["id"]

            if paciente_clicado_id != st.session_state.paciente_selecionado_id:
                st.session_state.paciente_selecionado_id = paciente_clicado_id
                st.session_state.modo_edicao_concluido = False
                st.rerun()

        st.divider()

        pacientes_concluidos_hoje = [
            p for p in lista_pacientes_hoje if p.get("Status") == "CONCLUÍDO"
        ]

        mapa_pacientes_completo = {
            p["id"]: p["Nome"] for p in pacientes_concluidos_hoje
        }
        opcoes_pacientes_susp = [p["Nome"] for p in pacientes_concluidos_hoje]

        paciente_para_editar_nome = st.selectbox(
            "✏️ EDITAR UM PACIENTE ESPECÍFICO (APENAS CONCLUÍDOS):",
            options=opcoes_pacientes_susp,
            index=None,
            placeholder="DIGITE OU SELECIONE O PACIENTE CONCLUÍDO...",
            key="select_habilitar_edicao",
        )

        if paciente_para_editar_nome:
            id_alvo = None
            for p_id, nome in mapa_pacientes_completo.items():
                if nome == paciente_para_editar_nome:
                    id_alvo = p_id
                    break

            if id_alvo is not None and (
                st.session_state.paciente_selecionado_id != id_alvo
                or not st.session_state.modo_edicao_concluido
            ):
                st.session_state.paciente_selecionado_id = id_alvo
                st.session_state.modo_edicao_concluido = True
                st.rerun()


# ABA 3: HISTÓRICO GERAL (OUTRAS DATAS E BUSCA)
with aba_historico:
    st.header("📂 HISTÓRICO GERAL DE ATENDIMENTOS")

    todos_pacientes = st.session_state.pacientes

    if not todos_pacientes:
        st.info("NENHUM REGISTRO DE ATENDIMENTO ENCONTRADO NA BASE DE DADOS.")
    else:
        df_historico = pd.DataFrame(todos_pacientes)

        df_historico["DATA DO REGISTRO"] = pd.to_datetime(
            df_historico["data_registro"]
        ).dt.strftime("%d/%m/%Y")

        col_busca, col_data_ini, col_data_fim = st.columns([2, 1, 1])

        with col_busca:
            termo_busca = st.text_input(
                "🔍 PESQUISAR POR NOME OU CPF:", placeholder="DIGITE AQUI..."
            )

        with col_data_ini:
            data_inicio = st.date_input(
                "DATA INICIAL", value=None, format="DD/MM/YYYY"
            )

        with col_data_fim:
            data_fim = st.date_input(
                "DATA FINAL", value=None, format="DD/MM/YYYY"
            )

        df_filtrado = df_historico.copy()

        if termo_busca.strip():
            termo = termo_busca.strip().upper()
            df_filtrado = df_filtrado[
                df_filtrado["Nome"].str.upper().str.contains(termo, na=False)
                | df_filtrado["CPF"].str.upper().str.contains(termo, na=False)
            ]

        if data_inicio:
            df_filtrado = df_filtrado[
                df_filtrado["data_registro"] >= data_inicio
            ]

        if data_fim:
            df_filtrado = df_filtrado[df_filtrado["data_registro"] <= data_fim]

        colunas_maiusculas = {
            "Horário de Chegada": "HORÁRIO DE CHEGADA",
            "Nome": "NOME",
            "CPF": "CPF",
            "Data de Nascimento": "DATA DE NASCIMENTO",
            "Atendimento": "ATENDIMENTO",
            "Profissional": "PROFISSIONAL",
            "Status": "STATUS",
            "Observações": "OBSERVAÇÕES",
        }

        df_filtrado = df_filtrado.rename(columns=colunas_maiusculas)

        colunas_historico = [
            "DATA DO REGISTRO",
            "HORÁRIO DE CHEGADA",
            "NOME",
            "CPF",
            "DATA DE NASCIMENTO",
            "ATENDIMENTO",
            "PROFISSIONAL",
            "STATUS",
            "OBSERVAÇÕES",
        ]

        df_exibicao_historico = df_filtrado[colunas_historico]

        st.subheader(f"REGISTROS ENCONTRADOS: {len(df_exibicao_historico)}")
        st.dataframe(
            df_exibicao_historico, use_container_width=True, hide_index=True
        )

        csv_buffer = io.BytesIO()
        df_exibicao_historico.to_csv(
            csv_buffer, index=False, encoding="utf-8-sig"
        )

        st.download_button(
            label="📥 BAIXAR HISTÓRICO FILTRADO EM CSV",
            data=csv_buffer.getvalue(),
            file_name=(
                "HISTORICO_ATENDIMENTOS_"
                f"{obter_hoje_brasilia().strftime('%d_%m_%Y')}.csv"
            ),
            mime="text/csv",
        )