import pandas as pd

from src.config import CAMINHO_PLANILHA_CONTROLE


COLUNAS_OBRIGATORIAS = [
    "AUTOMACAO",
    "STATUS",
    "LOCAL",
    "MATRICULA",
    "NOME DO AUTOR",
    "ADMISSAO",
    "DEMISSAO",
]


def ler_planilha_controle():
    """
    Lê a planilha de controle e retorna um DataFrame.
    """

    df = pd.read_excel(
        CAMINHO_PLANILHA_CONTROLE,
        engine="openpyxl",
        dtype={
            "AUTOMACAO": str,
            "STATUS": str,
            "LOCAL": str,
            "MATRICULA": str,
            "NOME DO AUTOR": str,
            "PRIORIDADE": str,
            "EMPRESA": str,
        }
    )

    return df


def validar_colunas_obrigatorias(df):
    """
    Verifica se a planilha possui as colunas obrigatórias.
    """

    colunas_faltantes = []

    for coluna in COLUNAS_OBRIGATORIAS:
        if coluna not in df.columns:
            colunas_faltantes.append(coluna)

    if colunas_faltantes:
        raise ValueError(
            f"As seguintes colunas obrigatórias não foram encontradas: {colunas_faltantes}"
        )


def linha_ja_processada(linha):
    """
    Verifica se a linha já foi processada.

    Considera processada quando AUTOMACAO = true.
    """

    valor = str(linha["AUTOMACAO"]).strip().lower()

    return valor == "true"


def marcar_linha_como_processada(df, indice):
    """
    Marca a linha no DataFrame como processada.
    """

    df.at[indice, "AUTOMACAO"] = "true"


def salvar_planilha_controle(df):
    """
    Salva a planilha de controle atualizada.
    """

    df.to_excel(
        CAMINHO_PLANILHA_CONTROLE,
        index=False,
        engine="openpyxl"
    )