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

    # Aplicação da sua correção: Leitura com UTF-8-SIG e tipagem forte
    return pd.read_csv(
        dados_memoria,
        sep=None,
        engine='python',
        encoding='utf-8-sig',
        dtype={'MATRICULA': str, 'REGISTRO': str}
    )


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
    """Garante que a nuvem receba o arquivo local Mestre mais atualizado."""
    if not CAMINHO_LOG_LOCAL.exists():
        return

    blob_client = obter_cliente_blob()
    caminho_azure = f"{PASTA_BLOB}/log_mestre.csv"
    blob_file = blob_client.get_blob_client(container=NOME_CONTAINER, blob=caminho_azure)

    with open(CAMINHO_LOG_LOCAL, "rb") as data:
        blob_file.upload_blob(data, overwrite=True)


def preparar_fila_execucao():
    """
    O Coração da Automação:
    1. Sobe backup caso tenha havido queda de energia ontem.
    2. Baixa o Mestre (que contém todo o histórico CONCLUIDO/EM ANDAMENTO).
    3. Puxa as planilhas do RH/Power Automate.
    4. Adiciona no Mestre apenas as matrículas que são novidade.
    5. Devolve a fila pronta para o bot rodar.
    """
    blob_client = obter_cliente_blob()

    # 1. Resgate de segurança
    sincronizar_log_local_com_nuvem()

    # 2. Carrega o Mestre atual (memória da automação)
    df_mestre = carregar_dados_do_blob(blob_client, "log_mestre.csv")

    if not df_mestre.empty and 'MATRICULA' in df_mestre.columns:
        df_mestre['MATRICULA'] = df_mestre['MATRICULA'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        matriculas_conhecidas = df_mestre['MATRICULA'].tolist()
    else:
        # Se for o primeiro dia da vida do robô ou arquivo vazio
        df_mestre = pd.DataFrame(
            columns=['MATRICULA', 'STATUS', 'ULTIMA_COMPETENCIA', 'DEMISSAO', 'ADMISSAO', 'DESLIGAMENTO'])
        matriculas_conhecidas = []

    # 3. Baixa as bases vivas (Ações Trabalhistas do Power Automate e Headcount)
    df_acoes = carregar_dados_do_blob(blob_client, "acoes_trabalhistas.csv")
    df_baixa = carregar_dados_do_blob(blob_client, "headcount_desligados.csv")

    df_acoes = padronizar_colunas(df_acoes,
                                  {'NOME_DO_AUTOR': 'NOME', 'DEMISSAO': 'DESLIGAMENTO', 'STATUS': 'STATUS_SISTEMA'})
    df_baixa = padronizar_colunas(df_baixa, {'UNIDADE': 'LOCAL', 'STATUS': 'STATUS_SISTEMA'})

    if not df_acoes.empty: df_acoes['PRIORIDADE_PESO'] = 1
    if not df_baixa.empty: df_baixa['PRIORIDADE_PESO'] = 2

    df_novos_brutos = pd.concat([df_acoes, df_baixa], ignore_index=True)

    # 4. Injeta as novidades sem apagar o histórico
    if not df_novos_brutos.empty and 'MATRICULA' in df_novos_brutos.columns:
        df_novos_brutos['MATRICULA'] = df_novos_brutos['MATRICULA'].astype(str).str.replace(r'\.0$', '',
                                                                                            regex=True).str.strip()
        df_novos_brutos = df_novos_brutos.sort_values('PRIORIDADE_PESO').drop_duplicates(subset=['MATRICULA'],
                                                                                         keep='first')

        # O Filtro Mágico: O "~" significa "NÃO ESTÁ EM".
        # Pega as linhas do CSV do RH que ainda NÃO existem no Mestre
        df_novos = df_novos_brutos[~df_novos_brutos['MATRICULA'].isin(matriculas_conhecidas)].copy()

        if not df_novos.empty:
            print(f"[{len(df_novos)}] novas matrículas detectadas nas bases de RH. Injetando no Mestre...")
            df_novos['ADMISSAO'] = converter_data_excel(df_novos['ADMISSAO'])
            df_novos['DESLIGAMENTO'] = converter_data_excel(df_novos['DESLIGAMENTO'])

            # Setup inicial para os novatos
            df_novos['STATUS'] = 'PENDENTE'
            df_novos['ULTIMA_COMPETENCIA'] = None

            # Concatena os novos funcionários no final da planilha mestre
            df_mestre = pd.concat([df_mestre, df_novos], ignore_index=True)

    # 5. Prepara os dados para o navegador
    df_mestre['ADMISSAO'] = pd.to_datetime(df_mestre['ADMISSAO'], errors='coerce')
    df_mestre['DESLIGAMENTO'] = pd.to_datetime(df_mestre['DESLIGAMENTO'], errors='coerce')

    # Atualiza o Ponto de Partida: Se estiver em andamento, o robô retoma da última competência
    df_mestre['DEMISSAO'] = np.where(
        df_mestre['STATUS'] == 'EM ANDAMENTO',
        pd.to_datetime(df_mestre['ULTIMA_COMPETENCIA'], errors='coerce'),
        df_mestre['DESLIGAMENTO']
    )

    # Limpa valores nulos na gravação para não sujar o CSV
    df_para_salvar = df_mestre.copy()
    if 'ULTIMA_COMPETENCIA' in df_para_salvar.columns:
        df_para_salvar['ULTIMA_COMPETENCIA'] = df_para_salvar['ULTIMA_COMPETENCIA'].astype(str).replace(
            ['NaT', 'nan', 'None'], '')

    # Salva o arquivo local e lança para o Azure (Atualiza a Fonte da Verdade)
    CAMINHO_LOG_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    df_para_salvar.to_csv(CAMINHO_LOG_LOCAL, index=False, sep=';', encoding='utf-8-sig')
    sincronizar_log_local_com_nuvem()

    # 6. Corta quem já acabou e devolve apenas a fila de trabalho
    df_fila = df_mestre[df_mestre['STATUS'] != 'CONCLUIDO'].copy()

    if 'PRIORIDADE_PESO' in df_fila.columns:
        df_fila = df_fila.sort_values(by=['PRIORIDADE_PESO', 'DESLIGAMENTO'], ascending=[True, True])

    df_fila = df_fila.dropna(subset=['ADMISSAO', 'DEMISSAO'])
    return df_fila.reset_index(drop=True)


def atualizar_log_local(matricula, status, ultima_competencia):
    """Atualiza o arquivo CSV linha a linha a cada PDF baixado"""
    if not CAMINHO_LOG_LOCAL.exists():
        return

    df_mestre = pd.read_csv(CAMINHO_LOG_LOCAL, sep=';', encoding='utf-8-sig', dtype={'MATRICULA': str})

    df_mestre['MATRICULA'] = df_mestre['MATRICULA'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    matricula_str = str(matricula).strip().replace('.0', '')

    df_mestre.loc[df_mestre['MATRICULA'] == matricula_str, 'STATUS'] = str(status)
    if ultima_competencia:
        df_mestre.loc[df_mestre['MATRICULA'] == matricula_str, 'ULTIMA_COMPETENCIA'] = str(ultima_competencia)

    df_mestre.to_csv(CAMINHO_LOG_LOCAL, index=False, sep=';', encoding='utf-8-sig')