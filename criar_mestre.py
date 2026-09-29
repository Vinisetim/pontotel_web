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

# Caminho de saída local
CAMINHO_LOG_LOCAL = Path("logs/log_mestre.csv")


def obter_cliente_blob():
    return BlobServiceClient.from_connection_string(STRING_CONEXAO_AZURE)


def carregar_dados_do_blob(blob_client, nome_arquivo):
    caminho_completo = f"{PASTA_BLOB}/{nome_arquivo}"
    blob = blob_client.get_blob_client(container=NOME_CONTAINER, blob=caminho_completo)

    if not blob.exists():
        print(f"Arquivo {nome_arquivo} não encontrado no Azure.")
        return pd.DataFrame()

    dados_memoria = io.BytesIO(blob.download_blob().readall())
    # engine='python' garante leitura fluida tanto para separador ',' quanto ';'
    return pd.read_csv(dados_memoria, sep=None, engine='python')


def padronizar_colunas(df, mapeamento):
    """Renomeia colunas específicas e força todas para MAIÚSCULO."""
    if not df.empty:
        df = df.rename(columns=mapeamento)
        df.columns = df.columns.str.upper()
    return df


def converter_data_excel(coluna_serie):
    """Garante a leitura correta das datas (formato serial do Excel ou texto normal)."""
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

    # Mapeamento exato com base nas colunas das suas duas planilhas originais
    # O status originário do RH vira STATUS_SISTEMA para não confundir com o da Automação.
    df_alta = padronizar_colunas(df_alta,
                                 {'NOME_DO_AUTOR': 'NOME', 'DEMISSAO': 'DESLIGAMENTO', 'STATUS': 'STATUS_SISTEMA'})
    df_baixa = padronizar_colunas(df_baixa, {'unidade': 'LOCAL', 'registro': 'MATRICULA', 'status': 'STATUS_SISTEMA'})

    if not df_alta.empty: df_alta['PRIORIDADE_PESO'] = 1
    if not df_baixa.empty: df_baixa['PRIORIDADE_PESO'] = 2

    # Concatenação e limpeza das matrículas (removendo .0 etc)
    df_cadastros = pd.concat([df_alta, df_baixa], ignore_index=True)
    df_cadastros['MATRICULA'] = df_cadastros['MATRICULA'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # Removemos nomes duplicados priorizando Ações Trabalhistas (peso 1)
    df_cadastros = df_cadastros.sort_values('PRIORIDADE_PESO').drop_duplicates(subset=['MATRICULA'], keep='first')

    df_cadastros['ADMISSAO'] = converter_data_excel(df_cadastros['ADMISSAO'])
    df_cadastros['DESLIGAMENTO'] = converter_data_excel(df_cadastros['DESLIGAMENTO'])

    print("Baixando histórico antigo de execuções para mesclagem...")
    df_estado = carregar_dados_do_blob(blob_client, "logs.csv")

    if not df_estado.empty:
        df_estado.columns = df_estado.columns.str.upper()
        df_estado['MATRICULA'] = df_estado['MATRICULA'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        # Filtramos do histórico antigo apenas as colunas de controle da automação
        colunas_historico = [c for c in ['MATRICULA', 'STATUS', 'ULTIMA_COMPETENCIA'] if c in df_estado.columns]

        # O Outer Join garante que não perderemos ninguém (junta as bases de RH com o log sem apagar linhas exclusivas)
        df_mestre = pd.merge(df_cadastros, df_estado[colunas_historico], on='MATRICULA', how='outer')

        # Quem veio apenas da base de RH e não estava no histórico recebe 'PENDENTE'
        df_mestre['STATUS'] = df_mestre['STATUS'].fillna('PENDENTE')
    else:
        # Se for a primeira vez que roda o projeto e não houver log antigo
        df_mestre = df_cadastros.copy()
        df_mestre['STATUS'] = 'PENDENTE'
        df_mestre['ULTIMA_COMPETENCIA'] = None

    # Ajusta o Ponto de Partida:
    # Se o robô caiu no meio de uma matriz EM ANDAMENTO, a data de partida da automação recua
    # para a ULTIMA_COMPETENCIA gerada, não para o desligamento original.
    df_mestre['DEMISSAO'] = np.where(
        df_mestre['STATUS'] == 'EM ANDAMENTO',
        pd.to_datetime(df_mestre['ULTIMA_COMPETENCIA'], errors='coerce'),
        df_mestre['DESLIGAMENTO']
    )

    print("Salvando log_mestre.csv localmente...")
    CAMINHO_LOG_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    df_mestre['MATRICULA'] = df_mestre['MATRICULA'].astype(str)

    # Previne que falhas "NaT" ou "None" gerem quebras de tipagem depois
    if 'ULTIMA_COMPETENCIA' in df_mestre.columns:
        df_mestre['ULTIMA_COMPETENCIA'] = df_mestre['ULTIMA_COMPETENCIA'].astype(str).replace('NaT', '').replace('None',
                                                                                                                 '')

    # Grava local com UTF-8 BOM e separador de ponto e vírgula
    df_mestre.to_csv(CAMINHO_LOG_LOCAL, index=False, sep=';', encoding='utf-8-sig')

    print("Fazendo upload do log_mestre.csv definitivo para o Azure...")
    caminho_azure = f"{PASTA_BLOB}/log_mestre.csv"
    blob_file = blob_client.get_blob_client(container=NOME_CONTAINER, blob=caminho_azure)
    with open(CAMINHO_LOG_LOCAL, "rb") as data:
        blob_file.upload_blob(data, overwrite=True)

    print(f"Sucesso! Arquivo Mestre criado com {len(df_mestre)} colaboradores. O main.py já pode rodar.")


if __name__ == "__main__":
    criar_arquivo_mestre()