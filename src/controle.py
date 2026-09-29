import pandas as pd
import io
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from pathlib import Path

load_dotenv()

STRING_CONEXAO_AZURE = os.getenv("AZURE_CONNECTION_STRING")
NOME_CONTAINER = "1-raw"
PASTA_BLOB = "processos-trabalhistas"

CAMINHO_LOG_LOCAL = Path("logs/log_mestre.csv")


def obter_cliente_blob():
    return BlobServiceClient.from_connection_string(STRING_CONEXAO_AZURE)


def carregar_mestre_do_blob(blob_client):
    """Baixa o log_mestre.csv do Azure e já salva localmente para garantir sincronia."""
    caminho_azure = f"{PASTA_BLOB}/log_mestre.csv"
    blob = blob_client.get_blob_client(container=NOME_CONTAINER, blob=caminho_azure)

    if not blob.exists():
        raise FileNotFoundError("O arquivo log_mestre.csv não está no Azure. Rode o script setup_mestre.py primeiro!")

    dados_memoria = io.BytesIO(blob.download_blob().readall())
    df_mestre = pd.read_csv(dados_memoria, sep=';', encoding='utf-8-sig', dtype={'MATRICULA': str})

    # Salva localmente para ser a base das edições célula a célula
    CAMINHO_LOG_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    df_mestre.to_csv(CAMINHO_LOG_LOCAL, index=False, sep=';', encoding='utf-8-sig')

    return df_mestre


def preparar_fila_execucao():
    """
    Apenas baixa o Mestre pronto do Azure, salva localmente e filtra a fila.
    Rápido, leve e centralizado.
    """
    blob_client = obter_cliente_blob()
    df_mestre = carregar_mestre_do_blob(blob_client)

    # Converte colunas de data para uso no bot
    df_mestre['ADMISSAO'] = pd.to_datetime(df_mestre['ADMISSAO'], errors='coerce')
    df_mestre['DEMISSAO'] = pd.to_datetime(df_mestre['DEMISSAO'], errors='coerce')
    df_mestre['DESLIGAMENTO'] = pd.to_datetime(df_mestre['DESLIGAMENTO'], errors='coerce')

    # Filtra só quem não terminou
    df_fila = df_mestre[df_mestre['STATUS'] != 'CONCLUIDO'].copy()

    if 'PRIORIDADE_PESO' in df_fila.columns:
        df_fila = df_fila.sort_values(by=['PRIORIDADE_PESO', 'DESLIGAMENTO'], ascending=[True, True])

    df_fila = df_fila.dropna(subset=['ADMISSAO', 'DEMISSAO'])
    return df_fila.reset_index(drop=True)


def atualizar_log_local(matricula, status, ultima_competencia):
    """
    Altera uma única célula no arquivo CSV Mestre local.
    Usado no main.py a cada relatório gerado.
    """
    if not CAMINHO_LOG_LOCAL.exists():
        return

    df_mestre = pd.read_csv(CAMINHO_LOG_LOCAL, sep=';', encoding='utf-8-sig', dtype={'MATRICULA': str})
    matricula_str = str(matricula).strip()

    df_mestre.loc[df_mestre['MATRICULA'] == matricula_str, 'STATUS'] = str(status)
    if ultima_competencia:
        df_mestre.loc[df_mestre['MATRICULA'] == matricula_str, 'ULTIMA_COMPETENCIA'] = str(ultima_competencia)

        # Ajusta a demissão caso o robô precise recomeçar amanhã (Ponto de Partida)
        df_mestre.loc[df_mestre['MATRICULA'] == matricula_str, 'DEMISSAO'] = str(ultima_competencia) + "-01"

    df_mestre.to_csv(CAMINHO_LOG_LOCAL, index=False, sep=';', encoding='utf-8-sig')


def sincronizar_log_local_com_nuvem():
    """Faz o upload da versão local atualizada do Mestre para o Azure."""
    if not CAMINHO_LOG_LOCAL.exists():
        return

    blob_client = obter_cliente_blob()
    caminho_azure = f"{PASTA_BLOB}/log_mestre.csv"
    blob_file = blob_client.get_blob_client(container=NOME_CONTAINER, blob=caminho_azure)

    with open(CAMINHO_LOG_LOCAL, "rb") as data:
        blob_file.upload_blob(data, overwrite=True)