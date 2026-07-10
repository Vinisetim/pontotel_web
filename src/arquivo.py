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
TEMPO_ESPERA_DOWNLOAD,
PASTA_SHAREPOINT_ARQUIVO,
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


def interpretar_local(local):
    """
    Interpreta o valor da coluna LOCAL da planilha.

    Exemplos:
    COM | Embu das Artes      -> negocio = Coletivo, unidade = Embu das Artes
    ESCOLAR | Embu das Artes  -> negocio = Escolar, unidade = Embu das Artes
    """

    local = str(local).strip()

    if "|" not in local:
        raise ValueError(
            f"Valor inválido na coluna LOCAL. Esperado formato 'TIPO | UNIDADE': {local}"
        )

    tipo, unidade = local.split("|", 1)

    tipo = tipo.strip().upper()
    unidade = unidade.strip()

    if "COM" in tipo:
        negocio = "Coletivo"
    else:
        negocio = "Escolar"

    return negocio, unidade


def interpretar_status(status):
    """
    Interpreta o valor da coluna STATUS da planilha.

    Ativo      -> 1_Ativos
    Desligado  -> 2_Desligados

    A pasta 3_Processos existe, mas não será usada neste contexto.
    """

    status = str(status).strip().upper()

    if status == "ATIVO":
        return "1_Ativos"

    if status == "DESLIGADO":
        return "2_Desligados"

    raise ValueError(
        f"Status inválido: {status}. Esperado 'Ativo' ou 'Desligado'."
    )


MAPA_PASTAS_UNIDADE = {
    "Coletivo": {
        "EMBU DAS ARTES": "Embu_das_Artes_Coletivo",
        "PORTO VELHO": "Porto_Velho",
        "BRAGANCA PAULISTA": "Braganca_Paulista_Coletivo",
        "BRAGANÇA PAULISTA": "Braganca_Paulista_Coletivo",
    },
    "Escolar": {
        "BARUERI": "Barueri",
        "BRAGANCA PAULISTA": "Braganca_Paulista_Escolar",
        "BRAGANÇA PAULISTA": "Braganca_Paulista_Escolar",
        "EMBU DAS ARTES": "Embu_das_Artes_Escolar",
        "EMBU GUACU": "Embu_Guaçu",
        "EMBU GUAÇU": "Embu_Guaçu",
        "ITAPECERICA DA SERRA": "Itapecerica_da_Serra",
        "OSASCO": "Osasco",
    }
}


def normalizar_chave_mapa(texto):
    """
    Normaliza um texto para ser usado como chave no mapa de unidades.
    """

    texto = str(texto).strip().upper()

    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def obter_nome_pasta_unidade(negocio, unidade):
    """
    Retorna o nome real da pasta da unidade dentro do SharePoint sincronizado.
    """

    chave_unidade = normalizar_chave_mapa(unidade)

    mapa_negocio = MAPA_PASTAS_UNIDADE.get(negocio)

    if not mapa_negocio:
        raise ValueError(f"Negócio não mapeado: {negocio}")

    nome_pasta = mapa_negocio.get(chave_unidade)

    if not nome_pasta:
        raise ValueError(
            f"Unidade não mapeada para o negócio {negocio}: {unidade}"
        )

    return nome_pasta

def montar_caminho_base_status(local, status):
    """
    Monta o caminho base até a pasta de status.

    Estrutura:
    PASTA_SHAREPOINT_ARQUIVO / negocio / pasta_unidade / pasta_status
    """

    negocio, unidade = interpretar_local(local)

    nome_pasta_unidade = obter_nome_pasta_unidade(
        negocio=negocio,
        unidade=unidade,
    )

    pasta_status = interpretar_status(status)

    caminho_base = (
        PASTA_SHAREPOINT_ARQUIVO
        / negocio
        / nome_pasta_unidade
        / pasta_status
    )

    return caminho_base

def localizar_pasta_colaborador(caminho_base_status, matricula):
    """
    Localiza a pasta do colaborador dentro da pasta de status.

    A busca usa o padrão:
    00[matricula]*

    Exemplo:
    matricula = 1428
    padrão = 001428*
    """

    matricula = str(matricula).strip()

    padrao_busca = f"00{matricula}*"

    pastas_encontradas = [
        caminho
        for caminho in caminho_base_status.glob(padrao_busca)
        if caminho.is_dir()
    ]

    if not pastas_encontradas:
        raise FileNotFoundError(
            f"Nenhuma pasta encontrada para a matrícula {matricula} em {caminho_base_status}"
        )

    if len(pastas_encontradas) > 1:
        raise ValueError(
            f"Mais de uma pasta encontrada para a matrícula {matricula}: {pastas_encontradas}"
        )

    return pastas_encontradas[0]

def obter_pasta_espelho_ponto(pasta_colaborador):
    """
    Cria ou retorna a pasta 'Espelho de Ponto Pontotel'
    dentro da pasta do colaborador.
    """

    pasta_espelho = pasta_colaborador / "Espelho de Ponto Pontotel"

    pasta_espelho.mkdir(parents=True, exist_ok=True)

    return pasta_espelho

def mover_pdf_para_pasta_espelho(caminho_pdf, pasta_espelho, matricula, nome, competencia):
    """
    Renomeia e move o PDF extraído para a pasta Espelho de Ponto Pontotel.

    Padrão do arquivo final:
    [matricula]-[nome]-[competencia].pdf
    """

    matricula_normalizada = normalzar_nome_arquivo(matricula)
    nome_normalizado = normalzar_nome_arquivo(nome)

    nome_arquivo_final = f"{matricula_normalizada}-{nome_normalizado}-{competencia}.pdf"

    caminho_final = pasta_espelho / nome_arquivo_final

    if caminho_final.exists():
        raise FileExistsError(f"O arquivo final já existe: {caminho_final}")

    shutil.move(str(caminho_pdf), str(caminho_final))

    return caminho_final

def processar_zip_relatorio(caminho_zip, matricula, nome, competencia, local, status):
    """
    Processa o ZIP baixado do PontoTel e move o PDF final para a pasta correta.
    """

    caminho_base_status = montar_caminho_base_status(
        local=local,
        status=status
    )

    pasta_colaborador = localizar_pasta_colaborador(
        caminho_base_status=caminho_base_status,
        matricula=matricula
    )

    pasta_espelho = obter_pasta_espelho_ponto(
        pasta_colaborador=pasta_colaborador
    )

    pasta_extraida = extrair_zip(
        caminho_zip=caminho_zip
    )

    caminho_pdf = localizar_pdf_extraido(
        pasta_extraida=pasta_extraida
    )

    caminho_final = mover_pdf_para_pasta_espelho(
        caminho_pdf=caminho_pdf,
        pasta_espelho=pasta_espelho,
        matricula=matricula,
        nome=nome,
        competencia=competencia
    )

    return caminho_final