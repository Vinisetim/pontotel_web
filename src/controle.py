import pandas as pd
from src.config import CAMINHO_PLANILHA_CONTROLE

COLUNAS_OBRIGATORIAS =[
    "MATRICULA",
    "NOME DO AUTOR",
    "ADMISSÃO",
    "DEMISSAO",
]

def ler_planilha():
    """Lê a planilha de controle"""
    df = pd.read_excel(CAMINHO_PLANILHA_CONTROLE,
                       engine="openpyxl",
                       dtype={
                           "MATRICULA": str,
                           "NOME DO AUTOR": str,
                           "PRIORIDADE": str,
                       })

    return df

def validar_colunas(df):
    """Verificação de colunas obrigatorias"""

    colunas_planilha = list(df.columns)

    colunas_faltantes = []

    for coluna in COLUNAS_OBRIGATORIAS:
        if coluna not in colunas_planilha:
            colunas_faltantes.append(coluna)

    if colunas_faltantes:
        raise(
            ValueError(
                f"As seguintes colunas não foram encontradas: {colunas_faltantes}"
            )
        )
