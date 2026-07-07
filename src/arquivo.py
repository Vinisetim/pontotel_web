import os
import re
import time
import shutil
import zipfile
import unicodedata
from pathlib import Path

from src.config import (
PASTA_DOWNLOADS,
PASTA_PROCESSAMENTO,
PASTA_OUTPUT,
TEMPO_ESPERA_DOWNLOAD
)

def normalzar_nome_arquivo(texto):
    """Normaliza um texto para que possa ser usado de nome de arquivo"""

    texto = str(texto).strip().upper()

    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")

    texto = re.sub(r'[\\/:*?"<>|]', "", texto)
    texto = re.sub(r"\s+", "_", texto)
    texto = re.sub(r"_+", "_", texto)

    return texto.strip("_")

def obter_arquivos_atuais_download():
    """Retorna conjuto de arquivos existentes na pasta downloads"""

    return set(PASTA_DOWNLOADS.glob("*"))


def esperar_arquivo_estavel(caminho_arquivo, timeout=60, intervalo=1):
    """
    Aguarda até que o arquivo pare de mudar de tamanho.

    Isso evita tentar extrair um ZIP que ainda está sendo finalizado pelo navegador.
    """

    tempo_inicial = time.time()
    tamanho_anterior = -1

    while True:
        if not caminho_arquivo.exists():
            time.sleep(intervalo)
            continue

        tamanho_atual = caminho_arquivo.stat().st_size

        if tamanho_atual == tamanho_anterior and tamanho_atual > 0:
            return caminho_arquivo

        tamanho_anterior = tamanho_atual

        if time.time() - tempo_inicial > timeout:
            raise TimeoutError(f"Arquivo não estabilizou dentro do tempo limite: {caminho_arquivo}")

        time.sleep(intervalo)

def esperar_novo_zip(arquivos_antes, timeout=TEMPO_ESPERA_DOWNLOAD):
    """Aguarda até que um novo arquivo zip apareça na pasta downloads"""

    tempo_inicial = time.time()

    while True:
        arquivos_agora = set(PASTA_DOWNLOADS.glob("*"))

        arquivos_novos = arquivos_agora-arquivos_antes

        arquivos_temporarios = [
            arquivo for arquivo in arquivos_novos
            if arquivo.suffix in [".crdownload", ".part", ".tmp"]
        ]

        arquivos_zip_novos = [
            arquivo for arquivo in arquivos_novos
            if arquivo.suffix == ".zip"
        ]

        if arquivos_zip_novos and not arquivos_temporarios:
            zip_baixado = max(arquivos_zip_novos, key=lambda arquivo:
                              arquivo.stat().st_mtime)
            esperar_arquivo_estavel(zip_baixado)
            return zip_baixado

        if time.time() - tempo_inicial > timeout:
            raise TimeoutError("Tempo excedido, esperando novo arquivo ZIP ser baixado")

        time.sleep(2)


def limpar_pasta_processamento():
    """
    Limpa a pasta de processamento antes de extrair um novo ZIP.
    """

    if PASTA_PROCESSAMENTO.exists():
        shutil.rmtree(PASTA_PROCESSAMENTO)

    PASTA_PROCESSAMENTO.mkdir(parents=True, exist_ok=True)

def extrair_zip(caminho_zip):
    """Extrai zip baixado para a pasta de processamento"""

    limpar_pasta_processamento()

    with zipfile.ZipFile(caminho_zip, "r") as arquivo_zip:
        arquivo_zip.extractall(PASTA_PROCESSAMENTO)

    return PASTA_PROCESSAMENTO

def localizar_pdf_extraido(pasta_extraida):
    """Localiza o PDF extraido do ZIP"""

    arquivos_pdf = list(Path(pasta_extraida).glob("*.pdf"))

    if not arquivos_pdf:
        raise FileNotFoundError(f"Nenhum arquivo PDF dentro do zip")

    if len(arquivos_pdf) > 1:
        raise ValueError("Mais de 1 PDF encontrado dentro do zip")

    return arquivos_pdf[0]


