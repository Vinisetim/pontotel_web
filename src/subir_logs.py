import pandas as pd
import io
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from pathlib import Path
from config import CAMINHO_PLANILHA_CONTROLE
# Configurações do ambiente
load_dotenv()
STRING_CONEXAO_AZURE = os.getenv("AZURE_CONNECTION_STRING")
NOME_CONTAINER = "1-raw"
PASTA_BLOB = "processos-trabalhistas"

# Caminho da sua planilha antiga local
CAMINHO_PLANILHA = CAMINHO_PLANILHA_CONTROLE


def migrar_historico_para_azure():
    print("Lendo a planilha de controle antiga local...")

    # Lê a planilha forçando a matrícula como texto para preservar os zeros à esquerda
    df_antigo = pd.read_excel(CAMINHO_PLANILHA, engine="openpyxl", dtype={"MATRICULA": str})

    def normalizar_status(valor):
        """Converte as marcações antigas da coluna AUTOMACAO para os status novos."""
        if pd.isna(valor):
            return "PENDENTE"
        val = str(valor).strip().upper()
        if val in {"TRUE", "CONCLUIDO", "CONCLUÍDO"}:
            return "CONCLUIDO"
        if val == "EM ANDAMENTO":
            return "EM ANDAMENTO"
        return "PENDENTE"

    # Descobre o status real com base na coluna antiga
    df_antigo['STATUS_NOVO'] = df_antigo['AUTOMACAO'].apply(normalizar_status)

    # Filtra apenas quem já começou ou já terminou
    df_migrar = df_antigo[df_antigo['STATUS_NOVO'] != 'PENDENTE'].copy()

    if df_migrar.empty:
        print("Nenhuma linha em andamento ou concluída encontrada na planilha antiga. Nada a migrar.")
        return

    # Limpeza rigorosa da matrícula
    df_migrar['MATRICULA'] = df_migrar['MATRICULA'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # Extrai a última competência gravada no processo anterior e formata para AAAA-MM
    df_migrar['ULTIMA_COMPETENCIA'] = pd.to_datetime(df_migrar['DEMISSAO'], errors='coerce').dt.strftime('%Y-%m')

    # Prepara o DataFrame final com as colunas essenciais
    df_final = df_migrar[['MATRICULA', 'STATUS_NOVO', 'ULTIMA_COMPETENCIA']].copy()
    df_final.rename(columns={'STATUS_NOVO': 'STATUS'}, inplace=True)

    # Garante que tudo seja string para evitar conflitos no CSV
    df_final['MATRICULA'] = df_final['MATRICULA'].astype(str)
    df_final['STATUS'] = df_final['STATUS'].astype(str)
    df_final['ULTIMA_COMPETENCIA'] = df_final['ULTIMA_COMPETENCIA'].astype(str)

    print(f"Encontrados {len(df_final)} colaboradores no histórico. Enviando para o Azure como CSV...")

    # Conecta no Azure e aponta para o arquivo logs.csv dentro da pasta processos-trabalhistas
    caminho_blob = f"{PASTA_BLOB}/logs.csv"
    blob_client = BlobServiceClient.from_connection_string(STRING_CONEXAO_AZURE).get_blob_client(
        container=NOME_CONTAINER, blob=caminho_blob)

    memoria_csv = io.BytesIO()
    # Salva em formato CSV com separador ';' e codificação utf-8-sig (perfeito para Excel e Power BI)
    df_final.to_csv(memoria_csv, index=False, sep=';', encoding='utf-8-sig')
    memoria_csv.seek(0)

    blob_client.upload_blob(memoria_csv, overwrite=True)

    print("Sucesso! Histórico migrado para o Azure. A nova automação já pode ser executada.")


if __name__ == "__main__":
    migrar_historico_para_azure()