from datetime import datetime
import io
import pandas as pd
import requests
import streamlit as st
import unicodedata
from zoneinfo import ZoneInfo


def obter_agora_brasil():
    return datetime.now(ZoneInfo("America/Sao_Paulo"))


st.set_page_config(layout="wide", page_title="Consulta de Responsável")

FILE_ID = "1rT9aAhZGdXF187Ss1IfqXP090itzbVeVS5aDqQKQ1vs"
EXCEL_URL = (
    f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=xlsx"
)

HORARIOS_CADASTRO = {
    "ANDREA": "Segunda a Sexta, das 08:00 às 09:00",
    "ALCIONE": "Segunda a Sexta, das 08:00 às 09:00",
    "CRISTIANE": "Segunda a Sexta, das 08:00 às 09:00",
    "LILI": "Segunda a Sexta, das 08:00 às 09:00",
    "MARINÊS": "Segunda a Sexta, das 08:00 às 09:00",
    "ROSE": "Segunda a Sexta, das 08:00 às 09:00",
    "GLEICE": "Quinta e Sexta, das 08:00 às 09:00",
    "PAULA": "Terça, Quinta e Sexta das 08:00 às 09:00",
    "GEISON": "Segunda, Terça e Sexta, das 08:00 às 09:00",
}

CORES_EQUIPES = {
    "EQ AZUL": {
        "bg": "#0548ff",
        "border": "#f8fafd",
        "text": "#dbeafe",
        "emoji": "🔵",
    },
    "EQ AMARELA": {
        "bg": "#fbff18",
        "border": "#f3f0e7",
        "text": "#11110d",
        "emoji": "🟡",
    },
    "EQ VERDE": {
        "bg": "#13b454",
        "border": "#f1f3f2",
        "text": "#e6f1ea",
        "emoji": "🟢",
    },
}


@st.cache_data(ttl=600)
def load_data_from_drive(url: str):
  response = requests.get(url)
  response.raise_for_status()
  df_raw = pd.read_excel(io.BytesIO(response.content), header=None)

  rua_col = df_raw.iloc[2:, 0].reset_index(drop=True)
  col_info = []
  current_equipe = None

  for col_idx in range(1, df_raw.shape[1]):
    eq_val = df_raw.iloc[0, col_idx]
    if pd.notna(eq_val) and str(eq_val).strip():
      current_equipe = str(eq_val).strip()

    resp_val = df_raw.iloc[1, col_idx]
    if pd.notna(resp_val) and str(resp_val).strip():
      col_info.append({
          "col_idx": col_idx,
          "equipe": current_equipe,
          "responsavel": str(resp_val).strip(),
      })

  return df_raw, rua_col, col_info


try:
  df_raw, rua_col, col_info = load_data_from_drive(EXCEL_URL)
except Exception:
  st.error("Erro ao carregar a planilha do Google Drive.")
  st.stop()


def normalize(text: str) -> str:
  if not isinstance(text, str):
    text = str(text) if pd.notna(text) else ""
  return "".join(
      c
      for c in unicodedata.normalize("NFKD", text).lower()
      if not unicodedata.combining(c)
  ).strip()


st.title("Consulta de ACS e ESF por Endereço")

rua_input = st.text_input("Nome da rua")
numero_input = st.text_input("Número")

if rua_input and numero_input:
  norm_rua_input = normalize(rua_input)
  norm_numero_input = normalize(numero_input)

  matching_indices = [
      idx for idx, r in enumerate(rua_col) if norm_rua_input in normalize(r)
  ]

  if not matching_indices:
    st.warning(f"A rua '{rua_input}' não foi encontrada na planilha.")
  else:
    responsaveis_encontrados = []

    for idx in matching_indices:
      nome_rua = rua_col.iloc[idx]
      row_data_idx = idx + 2

      for col in col_info:
        cell_value = str(df_raw.iloc[row_data_idx, col["col_idx"]])
        if pd.notna(cell_value) and cell_value.strip() != "nan":
          numeros = [n.strip() for n in cell_value.split(",") if n.strip()]
          if norm_numero_input in numeros:
            responsavel_nome = col["responsavel"]
            equipe_nome = col["equipe"] or "Não identificada"
            horario_cad = HORARIOS_CADASTRO.get(
                responsavel_nome.upper(), "Horário não informado"
            )
            responsaveis_encontrados.append({
                "Rua": nome_rua,
                "Número": numero_input.strip(),
                "Responsável (ACS)": responsavel_nome,
                "Equipe": equipe_nome,
                "Horário de Cadastro": horario_cad,
            })

    if responsaveis_encontrados:
      st.success("Responsável encontrado!")
      res_df = pd.DataFrame(responsaveis_encontrados)
      st.dataframe(res_df, hide_index=True)

      for item in responsaveis_encontrados:
        eq_key = item["Equipe"].upper().strip()
        estilo = CORES_EQUIPES.get(
            eq_key,
            {
                "bg": "#1f2937",
                "border": "#6b7280",
                "text": "#f3f4f6",
                "emoji": "📌",
            },
        )
        card_html = f"""
                <div style="
                    background-color: {estilo['bg']};
                    border-left: 5px solid {estilo['border']};
                    color: {estilo['text']};
                    padding: 14px 18px;
                    border-radius: 8px;
                    margin-top: 10px;
                    font-size: 16px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                ">
                    {estilo['emoji']} <strong>{item['Responsável (ACS)']}</strong> ({item['Equipe']}) — 
                    <strong>Horário de Cadastro:</strong> {item['Horário de Cadastro']}
                </div>
                """
        st.markdown(card_html, unsafe_allow_html=True)
    else:
      st.warning(
          f"Nenhum responsável encontrado para o número {numero_input} na"
          f" rua '{rua_input}'."
      )