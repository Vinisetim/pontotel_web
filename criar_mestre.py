import pandas as pd
import numpy as np
import io
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from pathlib import Path

# Carrega variáveis de ambiente
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

def padronizar_colunas(df, mapeamento):
    """Força as colunas para maiúsculo e garante que REGISTRO sempre vire MATRICULA."""
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


def criar_arquivo_mestre():
    print("Conectando ao Azure Blob Storage...")
    blob_client = obter_cliente_blob()

    print("Baixando bases brutas do RH...")
    df_alta = carregar_dados_do_blob(blob_client, "acoes_trabalhistas.csv")
    df_baixa = carregar_dados_do_blob(blob_client, "headcount_desligados.csv")

    df_alta = padronizar_colunas(df_alta,
                                 {'NOME_DO_AUTOR': 'NOME', 'DEMISSAO': 'DESLIGAMENTO', 'STATUS': 'STATUS_SISTEMA'})
    df_baixa = padronizar_colunas(df_baixa, {'UNIDADE': 'LOCAL', 'STATUS': 'STATUS_SISTEMA'})

    if not df_alta.empty: df_alta['PRIORIDADE_PESO'] = 1
    if not df_baixa.empty: df_baixa['PRIORIDADE_PESO'] = 2

    df_cadastros = pd.concat([df_alta, df_baixa], ignore_index=True)

    if 'MATRICULA' in df_cadastros.columns:
        df_cadastros['MATRICULA'] = df_cadastros['MATRICULA'].astype(str).str.replace(r'\.0$', '',
                                                                                      regex=True).str.strip()
        df_cadastros = df_cadastros.sort_values('PRIORIDADE_PESO').drop_duplicates(subset=['MATRICULA'], keep='first')

    df_cadastros['ADMISSAO'] = converter_data_excel(df_cadastros['ADMISSAO'])
    df_cadastros['DESLIGAMENTO'] = converter_data_excel(df_cadastros['DESLIGAMENTO'])

    print("Consolidando histórico real de execuções...")

    # Baixamos TODOS os logs que existem para extrair o melhor status possível
    df_mestre_antigo = carregar_dados_do_blob(blob_client, "log_mestre.csv")
    df_log_legado = carregar_dados_do_blob(blob_client, "logs.csv")

    df_estado = pd.DataFrame()

    if not df_mestre_antigo.empty:
        df_estado = pd.concat([df_estado, padronizar_colunas(df_mestre_antigo, {})], ignore_index=True)
    if not df_log_legado.empty:
        df_estado = pd.concat([df_estado, padronizar_colunas(df_log_legado, {})], ignore_index=True)

    if not df_estado.empty and 'MATRICULA' in df_estado.columns:
        df_estado['MATRICULA'] = df_estado['MATRICULA'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        # Atribui peso aos status. CONCLUIDO sempre vence EM ANDAMENTO, que vence PENDENTE.
        df_estado['STATUS'] = df_estado['STATUS'].astype(str).str.upper().str.strip().replace(
            {'CONCLUÍDO': 'CONCLUIDO'})
        pesos_status = {'PENDENTE': 1, 'EM ANDAMENTO': 2, 'CONCLUIDO': 3}
        df_estado['PESO_STATUS'] = df_estado['STATUS'].map(pesos_status).fillna(0)

        # Ordena pelo peso e mantém apenas a linha com o maior peso de cada matrícula
        df_estado = df_estado.sort_values(by=['MATRICULA', 'PESO_STATUS'])
        df_estado = df_estado.drop_duplicates(subset=['MATRICULA'], keep='last')

        colunas_historico = [c for c in ['MATRICULA', 'STATUS', 'ULTIMA_COMPETENCIA'] if c in df_estado.columns]
        df_mestre = pd.merge(df_cadastros, df_estado[colunas_historico], on='MATRICULA', how='outer')
        df_mestre['STATUS'] = df_mestre['STATUS'].fillna('PENDENTE')
    else:
        df_mestre = df_cadastros.copy()
        df_mestre['STATUS'] = 'PENDENTE'
        df_mestre['ULTIMA_COMPETENCIA'] = None

    df_mestre['DEMISSAO'] = np.where(
        df_mestre['STATUS'] == 'EM ANDAMENTO',
        pd.to_datetime(df_mestre['ULTIMA_COMPETENCIA'], errors='coerce'),
        df_mestre['DESLIGAMENTO']
    )

    print("Salvando log_mestre.csv localmente...")
    CAMINHO_LOG_LOCAL.parent.mkdir(parents=True, exist_ok=True)

    if 'MATRICULA' in df_mestre.columns:
        df_mestre['MATRICULA'] = df_mestre['MATRICULA'].astype(str)

    if 'ULTIMA_COMPETENCIA' in df_mestre.columns:
        df_mestre['ULTIMA_COMPETENCIA'] = df_mestre['ULTIMA_COMPETENCIA'].astype(str).replace('NaT', '').replace('nan',
                                                                                                                 '').replace(
            'None', '')

    df_mestre.to_csv(CAMINHO_LOG_LOCAL, index=False, sep=';', encoding='utf-8-sig')

    print("Fazendo upload do log_mestre.csv definitivo para o Azure...")
    caminho_azure = f"{PASTA_BLOB}/log_mestre.csv"
    blob_file = blob_client.get_blob_client(container=NOME_CONTAINER, blob=caminho_azure)

    with open(CAMINHO_LOG_LOCAL, "rb") as data:
        blob_file.upload_blob(data, overwrite=True)

    print(f"Sucesso! Arquivo Mestre recuperado e criado com {len(df_mestre)} colaboradores.")


if __name__ == "__main__":
    criar_arquivo_mestre()