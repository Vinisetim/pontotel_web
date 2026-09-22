import os
from datetime import datetime
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()
STRING_CONEXAO_AZURE = os.getenv("AZURE_CONNECTION_STRING")
NOME_CONTAINER = "1-raw"


def registrar_ocorrencia(tipo, matricula, nome=None, competencia=None, detalhes=None):
    """
    Envia uma nova linha estruturada em CSV para o Append Blob no Azure.
    """
    data_atual = datetime.now().strftime("%Y-%m-%d")
    nome_arquivo_log = f"logs/ocorrencias_{data_atual}.csv"

    blob_service_client = BlobServiceClient.from_connection_string(STRING_CONEXAO_AZURE)
    blob_client = blob_service_client.get_blob_client(container=NOME_CONTAINER, blob=nome_arquivo_log)

    # Se o arquivo não existir, criamos e adicionamos a linha de cabeçalho
    if not blob_client.exists():
        blob_client.create_append_blob()
        # O utf-8-sig garante a leitura correta de acentos no Excel/Power BI
        cabecalho = "DATA_HORA;TIPO;MATRICULA;NOME;COMPETENCIA;DETALHES\n".encode('utf-8-sig')
        blob_client.append_block(cabecalho)

    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Higienização: Remove quebras de linha e pontos e vírgulas do texto de erro
    # para garantir que o CSV não pule colunas ou linhas acidentalmente.
    detalhes_limpo = str(detalhes).replace('\n', ' ').replace('\r', '').replace(';', ',') if detalhes else ""
    nome_limpo = str(nome).replace(';', ',') if nome else ""
    competencia_limpa = str(competencia) if competencia else ""
    matricula_limpa = str(matricula)

    # Monta a linha separada por ponto e vírgula
    linha_csv = f"{data_hora};{tipo};{matricula_limpa};{nome_limpo};{competencia_limpa};{detalhes_limpo}\n"

    # Injeta a linha codificada no final do blob
    blob_client.append_block(linha_csv.encode('utf-8'))
    print(f"Log registrado no Azure: {tipo} para matrícula {matricula}")