import pandas as pd
import numpy as np
import io
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

STRING_CONEXAO_AZURE = os.getenv("AZURE_CONNECTION_STRING")
NOME_CONTAINER = "1-raw"
PASTA_BLOB = "processos-trabalhistas"


def obter_cliente_blob():
    return BlobServiceClient.from_connection_string(STRING_CONEXAO_AZURE)


def carregar_dados_do_blob(blob_service_client, nome_arquivo, formato="csv"):
    caminho_completo = f"{PASTA_BLOB}/{nome_arquivo}"
    blob_client = blob_service_client.get_blob_client(container=NOME_CONTAINER, blob=caminho_completo)

    if not blob_client.exists():
        return pd.DataFrame()

    download_stream = blob_client.download_blob().readall()
    dados_memoria = io.BytesIO(download_stream)

    if formato == "csv":
        # O engine python com sep=None descobre sozinho se o arquivo usa ',' ou ';'
        return pd.read_csv(dados_memoria, sep=None, engine='python')


def padronizar_colunas(df, mapeamento):
    if not df.empty:
        df = df.rename(columns=mapeamento)
        df.columns = df.columns.str.upper()
    return df


def converter_data_excel(coluna_serie):
    numeros = pd.to_numeric(coluna_serie, errors='coerce')
    numeros = numeros.where(numeros > 30000, np.nan)
    datas_excel = pd.to_datetime(numeros, origin='1899-12-30', unit='D')
    datas_texto = pd.to_datetime(coluna_serie, errors='coerce', dayfirst=True, format='mixed')
    return datas_excel.fillna(datas_texto)


def preparar_fila_execucao():
    blob_client = obter_cliente_blob()

    df_alta = carregar_dados_do_blob(blob_client, "acoes_trabalhistas.csv")
    df_baixa = carregar_dados_do_blob(blob_client, "headcount_desligados.csv")

    df_alta = padronizar_colunas(df_alta,
                                 {'NOME_DO_AUTOR': 'NOME', 'DEMISSAO': 'DESLIGAMENTO', 'STATUS': 'STATUS_SISTEMA'})
    df_baixa = padronizar_colunas(df_baixa, {'unidade': 'LOCAL', 'registro': 'MATRICULA', 'status': 'STATUS_SISTEMA'})

    if not df_alta.empty:
        df_alta['PRIORIDADE_PESO'] = 1
    if not df_baixa.empty:
        df_baixa['PRIORIDADE_PESO'] = 2

    df_completo = pd.concat([df_alta, df_baixa], ignore_index=True)

    if 'MATRICULA' in df_completo.columns:
        df_completo['MATRICULA'] = df_completo['MATRICULA'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    df_completo = df_completo.sort_values('PRIORIDADE_PESO')
    df_completo = df_completo.drop_duplicates(subset=['MATRICULA'], keep='first')

    if 'ADMISSAO' in df_completo.columns:
        df_completo['ADMISSAO'] = converter_data_excel(df_completo['ADMISSAO'])
    if 'DESLIGAMENTO' in df_completo.columns:
        df_completo['DESLIGAMENTO'] = converter_data_excel(df_completo['DESLIGAMENTO'])

    # A leitura agora busca explicitamente o arquivo CSV
        # -------------------------------------------------------------------------
        # LEITURA E TRATAMENTO DO HISTÓRICO (LOGS.CSV)
        # -------------------------------------------------------------------------
        df_estado = carregar_dados_do_blob(blob_client, "logs.csv", formato="csv")

        # Valida se o arquivo veio preenchido e se realmente contém a coluna MATRICULA
        if not df_estado.empty:
            # Padroniza os cabeçalhos do estado para maiúsculo para evitar conflitos de nomes
            df_estado.columns = df_estado.columns.str.upper()

        if not df_estado.empty and 'MATRICULA' in df_estado.columns:
            df_estado['MATRICULA'] = df_estado['MATRICULA'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

            df_completo = pd.merge(
                df_completo,
                df_estado[['MATRICULA', 'STATUS', 'ULTIMA_COMPETENCIA']],
                on='MATRICULA',
                how='left'
            )
            df_completo = df_completo[df_completo['STATUS'] != 'CONCLUIDO']

            df_completo['DEMISSAO'] = np.where(
                df_completo['STATUS'] == 'EM ANDAMENTO',
                pd.to_datetime(df_completo['ULTIMA_COMPETENCIA'], errors='coerce'),
                df_completo['DESLIGAMENTO']
            )
        else:
            # Se o logs.csv estiver vazio ou corrompido, a automação assume que todos são pendentes
            print("Aviso: Arquivo logs.csv no Azure está vazio ou sem a coluna MATRICULA. Iniciando do zero.")
            df_completo['DEMISSAO'] = df_completo['DESLIGAMENTO']
            df_completo['STATUS'] = 'PENDENTE'
            df_completo['ULTIMA_COMPETENCIA'] = None

    df_completo = df_completo.sort_values(
        by=['PRIORIDADE_PESO', 'DESLIGAMENTO'],
        ascending=[True, True]
    )

    df_completo = df_completo.dropna(subset=['ADMISSAO', 'DEMISSAO'])
    return df_completo.reset_index(drop=True)


def salvar_estado_no_blob(df_estado):
    """
    Salva o DataFrame de progresso de volta no Azure como logs.csv,
    formatado para leitura perfeita no Excel e Power BI.
    """
    caminho_completo = f"{PASTA_BLOB}/logs.csv"
    blob_client = obter_cliente_blob().get_blob_client(container=NOME_CONTAINER, blob=caminho_completo)

    df_para_salvar = df_estado.copy()
    df_para_salvar['MATRICULA'] = df_para_salvar['MATRICULA'].astype(str)
    df_para_salvar['STATUS'] = df_para_salvar['STATUS'].astype(str)
    df_para_salvar['ULTIMA_COMPETENCIA'] = df_para_salvar['ULTIMA_COMPETENCIA'].astype(str)

    memoria_csv = io.BytesIO()
    # Grava o CSV na memória com separador ';' e codificação para o Excel
    df_para_salvar.to_csv(memoria_csv, index=False, sep=';', encoding='utf-8-sig')
    memoria_csv.seek(0)

    blob_client.upload_blob(memoria_csv, overwrite=True)