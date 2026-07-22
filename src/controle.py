import pandas as pd

from src.config import CAMINHO_PLANILHA_CONTROLE

STATUS_PENDENTE = "PENDENTE"
STATUS_EM_ANDAMENTO = "EM ANDAMENTO"
STATUS_CONCLUIDO = "CONCLUIDO"


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

def normalizar_status_automacao(valor):
    """Normaliza o valor da coluna automacao.
    true -> CONCLUIDO
    false -> PENDENTE
    Vazio ou NaN -> PENDENTE"""

    if pd.isna(valor):
        return valor

    valor_normalizado = str(valor).strip().upper()

    if valor_normalizado in {"TRUE", "CONCLUIDO", "CONCLUÍDO"}:
        return STATUS_CONCLUIDO

    return STATUS_PENDENTE

def linha_deve_ser_processada(linha):
    """retorna true se a linha precisa ser processada e false se não precisa ser processada."""
    status_automacao = normalizar_status_automacao(linha["AUTOMACAO"])
    return status_automacao != STATUS_CONCLUIDO


def atualizar_status_automacao(df, indice, novo_status):
    """Atualiza o status da coluna automacao no data-frame"""

    status_normalizado =str(novo_status).strip().upper()

    status_validos = {
        STATUS_PENDENTE,
        STATUS_EM_ANDAMENTO,
        STATUS_CONCLUIDO,
    }

    if status_normalizado not in status_validos:
        raise ValueError(
            f"status  da automação invalido: {novo_status}"
            f"Valores permitidos: {status_validos}"
        )

    df.at[indice, "AUTOMACAO"] = status_normalizado


def marcar_linha_em_andamento(df,indice):
    atualizar_status_automacao(
        df=df,
        indice=indice,
        novo_status=STATUS_EM_ANDAMENTO,
    )

def marcar_linha_como_concluida(df,indice):
    atualizar_status_automacao(
        df=df,
        indice=indice,
        novo_status=STATUS_CONCLUIDO,
    )

def atualizar_demissao(df, indice, competencia):
    print(f"Recebeu {competencia}")
    try:
        nova_demissao = pd.to_datetime(
            f"{competencia}-01",
            format="%Y-%m-%d",
        )

    except ValueError as erro:
        raise ValueError(
            "competencia invalida."
            "O formato esperado é AAAA-MM"
        ) from erro

    df.at[indice, "DEMISSAO"] = nova_demissao

def obter_competencia_anterior(competencia):
    data_competencia = pd.to_datetime(
        f"{competencia}-01",
        format="%Y-%m-%d",
    )
    print(f"Recebeu {competencia}")
    competencia_anterior = data_competencia-pd.DateOffset(months=1)

    return competencia_anterior.strftime("%Y-%m")

def registrar_competencia_concluida(df, indice, competencia):
    proxima_competencia_pendente = (obter_competencia_anterior(competencia))

    atualizar_demissao(df=df, indice=indice, competencia=proxima_competencia_pendente)



def salvar_planilha_controle(df):
    """
    Salva a planilha de controle atualizada.
    """
    df.to_excel(
        CAMINHO_PLANILHA_CONTROLE,
        index=False,
        engine="openpyxl"
    )