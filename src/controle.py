import pandas as pd
import numpy as np
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


def carregar_dados_do_blob(blob_client, nome_arquivo):
    caminho_completo = f"{PASTA_BLOB}/{nome_arquivo}"
    blob = blob_client.get_blob_client(container=NOME_CONTAINER, blob=caminho_completo)

    if not blob.exists():
        return pd.DataFrame()

    dados_memoria = io.BytesIO(blob.download_blob().readall())

    # Lemos o CSV forçando o encoding correto e tipando as chaves como texto
    return pd.read_csv(
        dados_memoria,
        sep=None,
        engine='python',
        encoding='utf-8-sig',
        dtype={'MATRICULA': str, 'REGISTRO': str}
    )

def carregar_mestre_do_blob(blob_client):
    caminho_azure = f"{PASTA_BLOB}/log_mestre.csv"
    blob = blob_client.get_blob_client(container=NOME_CONTAINER, blob=caminho_azure)

    if not blob.exists():
        raise FileNotFoundError("O log_mestre.csv não está no Azure. Rode criar_mestre.py primeiro!")

    dados_memoria = io.BytesIO(blob.download_blob().readall())
    df_mestre = pd.read_csv(dados_memoria, sep=';', encoding='utf-8-sig', dtype={'MATRICULA': str})

    CAMINHO_LOG_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    df_mestre.to_csv(CAMINHO_LOG_LOCAL, index=False, sep=';', encoding='utf-8-sig')

    return df_mestre


def padronizar_colunas(df, mapeamento):
    if not df.empty:
        df.columns = df.columns.str.upper()
        df = df.rename(columns=mapeamento)
        if 'REGISTRO' in df.columns and 'MATRICULA' not in df.columns:
            df = df.rename(columns={'REGISTRO': 'MATRICULA'})
    return df


def converter_data_excel(coluna_serie):
    numeros = pd.to_numeric(coluna_serie, errors='coerce')
    numeros = numeros.where(numeros > 30000, np.nan)
    datas_excel = pd.to_datetime(numeros, origin='1899-12-30', unit='D')
    datas_texto = pd.to_datetime(coluna_serie, errors='coerce', dayfirst=True, format='mixed')
    return datas_excel.fillna(datas_texto)


def sincronizar_log_local_com_nuvem():
    if not CAMINHO_LOG_LOCAL.exists():
        return

    blob_client = obter_cliente_blob()
    caminho_azure = f"{PASTA_BLOB}/log_mestre.csv"
    blob_file = blob_client.get_blob_client(container=NOME_CONTAINER, blob=caminho_azure)

    with open(CAMINHO_LOG_LOCAL, "rb") as data:
        blob_file.upload_blob(data, overwrite=True)


def preparar_fila_execucao():
    blob_client = obter_cliente_blob()

    # 1. UPLOAD DE SEGURANÇA: Garante o resgate de progresso local
    sincronizar_log_local_com_nuvem()

    # 2. Carrega a Base oficial
    df_mestre = carregar_mestre_do_blob(blob_client)

    # 3. Adiciona as entradas dinâmicas do Power Automate
    df_acoes = carregar_dados_do_blob(blob_client, "acoes_trabalhistas.csv")
    df_acoes = padronizar_colunas(df_acoes,
                                  {'NOME_DO_AUTOR': 'NOME', 'DEMISSAO': 'DESLIGAMENTO', 'STATUS': 'STATUS_SISTEMA'})

    if not df_acoes.empty and 'MATRICULA' in df_acoes.columns:
        df_acoes['MATRICULA'] = df_acoes['MATRICULA'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        matriculas_conhecidas = df_mestre['MATRICULA'].astype(str).tolist()

        df_novos = df_acoes[~df_acoes['MATRICULA'].isin(matriculas_conhecidas)].copy()

        if not df_novos.empty:
            print(f"[{len(df_novos)}] novas ações trabalhistas detectadas. Atualizando Mestre...")
            df_novos['ADMISSAO'] = converter_data_excel(df_novos['ADMISSAO'])
            df_novos['DESLIGAMENTO'] = converter_data_excel(df_novos['DESLIGAMENTO'])
            df_novos['PRIORIDADE_PESO'] = 1
            df_novos['STATUS'] = 'PENDENTE'
            df_novos['ULTIMA_COMPETENCIA'] = None
            df_novos['DEMISSAO'] = df_novos['DESLIGAMENTO']

            df_mestre = pd.concat([df_mestre, df_novos], ignore_index=True)
            df_mestre.to_csv(CAMINHO_LOG_LOCAL, index=False, sep=';', encoding='utf-8-sig')
            sincronizar_log_local_com_nuvem()

    df_mestre['ADMISSAO'] = pd.to_datetime(df_mestre['ADMISSAO'], errors='coerce')
    df_mestre['DEMISSAO'] = pd.to_datetime(df_mestre['DEMISSAO'], errors='coerce')
    df_mestre['DESLIGAMENTO'] = pd.to_datetime(df_mestre['DESLIGAMENTO'], errors='coerce')

    df_fila = df_mestre[df_mestre['STATUS'] != 'CONCLUIDO'].copy()

    if 'PRIORIDADE_PESO' in df_fila.columns:
        df_fila = df_fila.sort_values(by=['PRIORIDADE_PESO', 'DESLIGAMENTO'], ascending=[True, True])

    df_fila = df_fila.dropna(subset=['ADMISSAO', 'DEMISSAO'])
    return df_fila.reset_index(drop=True)


def atualizar_log_local(matricula, status, ultima_competencia):
    if not CAMINHO_LOG_LOCAL.exists():
        return

    df_mestre = pd.read_csv(CAMINHO_LOG_LOCAL, sep=';', encoding='utf-8-sig', dtype={'MATRICULA': str})

    # Higienização de garantia: limpa a base toda e a matrícula recebida para o .loc ser perfeito
    df_mestre['MATRICULA'] = df_mestre['MATRICULA'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    matricula_str = str(matricula).strip().replace('.0', '')

    df_mestre.loc[df_mestre['MATRICULA'] == matricula_str, 'STATUS'] = str(status)

    if ultima_competencia:
        df_mestre.loc[df_mestre['MATRICULA'] == matricula_str, 'ULTIMA_COMPETENCIA'] = str(ultima_competencia)
        df_mestre.loc[df_mestre['MATRICULA'] == matricula_str, 'DEMISSAO'] = str(ultima_competencia) + "-01"

    df_mestre.to_csv(CAMINHO_LOG_LOCAL, index=False, sep=';', encoding='utf-8-sig')