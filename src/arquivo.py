import re
import time
import shutil
import zipfile
import unicodedata
from pathlib import Path

from src.config import (
    PASTA_DOWNLOADS,
    PASTA_PROCESSAMENTO,
    TEMPO_ESPERA_DOWNLOAD,
    PASTA_SHAREPOINT_ARQUIVO,
)
from src.logs import registrar_ocorrencia

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
    """Aguarda até que o arquivo pare de mudar de tamanho."""
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

def esperar_novo_zip(arquivos_antes, timeout=TEMPO_ESPERA_DOWNLOAD, matricula=None, nome=None, competencia=None):
    """Aguarda um novo ZIP aparecer na pasta de downloads."""
    tempo_inicial = time.time()
    extensoes_temporarias = {".crdownload", ".part", ".tmp"}
    ultima_mensagem = 0

    while True:
        arquivos_agora = set(PASTA_DOWNLOADS.glob("*"))
        arquivos_novos = arquivos_agora - arquivos_antes

        arquivos_temporarios = [arq for arq in arquivos_novos if arq.suffix.lower() in extensoes_temporarias]
        arquivos_zip_novos = [arq for arq in arquivos_novos if arq.suffix.lower() == ".zip"]
        arquivos_nao_zip = [arq for arq in arquivos_novos if arq.suffix.lower() not in extensoes_temporarias and arq.suffix.lower() != ".zip"]

        if arquivos_temporarios:
            if time.time() - ultima_mensagem >= 30:
                print("Download ainda em andamento:", [arq.name for arq in arquivos_temporarios])
                ultima_mensagem = time.time()
            if timeout is not None and time.time() - tempo_inicial > timeout:
                raise TimeoutError("Tempo excedido aguardando o download temporário ser concluído.")
            time.sleep(2)
            continue

        if arquivos_zip_novos:
            zip_baixado = max(arquivos_zip_novos, key=lambda arquivo: arquivo.stat().st_mtime)
            esperar_arquivo_estavel(zip_baixado)
            print(f"Arquivo ZIP identificado: {zip_baixado}")
            return zip_baixado

        if arquivos_nao_zip:
            arquivo_invalido = max(arquivos_nao_zip, key=lambda arquivo: arquivo.stat().st_mtime)
            esperar_arquivo_estavel(arquivo_invalido)
            mensagem_erro = f"O download foi concluído, mas o arquivo gerado não é ZIP. Arquivo encontrado: {arquivo_invalido}"
            registrar_ocorrencia("ARQUIVO_BAIXADO_NAO_ZIP", matricula=(matricula if matricula is not None else "NAO_INFORMADA"), nome=nome, competencia=competencia, detalhes=mensagem_erro)
            raise FileNotFoundError(mensagem_erro)

        if timeout is not None and time.time() - tempo_inicial > timeout:
            raise TimeoutError("Tempo excedido esperando um novo arquivo ZIP ser baixado.")

        if time.time() - ultima_mensagem >= 30:
            print("Aguardando o download começar...")
            ultima_mensagem = time.time()

        time.sleep(2)

def limpar_pasta_processamento():
    """Limpa a pasta de processamento antes de extrair um novo ZIP."""
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
    arquivos_pdf = list(Path(pasta_extraida).rglob("*.pdf"))
    if not arquivos_pdf:
        raise FileNotFoundError("Nenhum arquivo PDF dentro do zip")
    if len(arquivos_pdf) > 1:
        raise ValueError("Mais de 1 PDF encontrado dentro do zip")
    return arquivos_pdf[0]

def interpretar_local(local):
    """Interpreta o valor da coluna LOCAL da planilha para separar Negócio e Unidade."""
    local = str(local).strip()
    if local.upper() == "MATRIZ":
        return "Matriz", None

    if "|" not in local:
        raise ValueError(f"Valor inválido na coluna LOCAL. Esperado formato 'TIPO | UNIDADE': {local}")

    tipo, unidade = local.split("|", 1)
    tipo = tipo.strip().upper()
    unidade = unidade.strip()

    if "MATRIZ" in tipo:
        negocio = "Matriz"
    elif "COM" in tipo:
        negocio = "Coletivo"
    else:
        negocio = "Escolar"
    return negocio, unidade

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
    """Normaliza um texto para ser usado como chave no mapa de unidades."""
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()

def obter_nome_pasta_unidade(negocio, unidade):
    """Retorna o nome real da pasta da unidade dentro do SharePoint."""
    chave_unidade = normalizar_chave_mapa(unidade)
    mapa_negocio = MAPA_PASTAS_UNIDADE.get(negocio)

    if not mapa_negocio:
        raise ValueError(f"Negócio não mapeado: {negocio}")

    nome_pasta = mapa_negocio.get(chave_unidade)
    if not nome_pasta:
        raise ValueError(f"Unidade não mapeada para o negócio {negocio}: {unidade}")

    return nome_pasta

def montar_caminho_base_desligamento(local, data_desligamento):
    """
    Monta o caminho base dinâmico até a pasta de desligamentos.
    Estrutura: raiz / unidade-negocio / ano(YYYY) / mes(MM) / desligamentos
    """
    negocio, unidade = interpretar_local(local)

    if negocio == "Matriz":
        pasta_unidade = "Matriz"
    else:
        pasta_unidade = obter_nome_pasta_unidade(negocio=negocio, unidade=unidade)

    # O strftime extrai o Ano e o Mês formatados com base na data real da demissão.
    ano = data_desligamento.strftime("%Y")
    mes = data_desligamento.strftime("%m")

    # Constroi o caminho usando as barras nativas da biblioteca Path do Python
    return PASTA_SHAREPOINT_ARQUIVO / pasta_unidade / ano / mes / "desligamentos"

def localizar_pasta_colaborador(caminho_base, matricula):
    """Localiza a pasta do colaborador usando o padrão 00[matricula]*"""
    matricula = str(matricula).strip()
    matricula_formatada = matricula.zfill(6)
    padrao_busca = f"{matricula_formatada}*"

    pastas_encontradas = [caminho for caminho in caminho_base.glob(padrao_busca) if caminho.is_dir()]

    if not pastas_encontradas:
        mensagem_erro = f"Nenhuma pasta encontrada para a matrícula {matricula} em {caminho_base}"
        registrar_ocorrencia(tipo="PASTA_NAO_ENCONTRADA", matricula=matricula, detalhes=mensagem_erro)
        raise FileNotFoundError(mensagem_erro)

    if len(pastas_encontradas) > 1:
        raise ValueError(f"Mais de uma pasta encontrada para a matrícula {matricula}: {pastas_encontradas}")

    return pastas_encontradas[0]

def obter_pasta_espelho_ponto(pasta_colaborador):
    """Cria ou retorna a pasta 'Espelho de Ponto Pontotel'."""
    pasta_espelho = pasta_colaborador / "Espelho de Ponto Pontotel"
    pasta_espelho.mkdir(parents=True, exist_ok=True)
    return pasta_espelho

def mover_pdf_para_pasta_espelho(caminho_pdf, pasta_espelho, matricula, nome, competencia):
    """Renomeia e move o PDF extraído."""
    matricula_normalizada = normalzar_nome_arquivo(matricula)
    nome_normalizado = normalzar_nome_arquivo(nome)

    nome_arquivo_final = f"{competencia}.pdf"
    caminho_final = pasta_espelho / nome_arquivo_final

    if caminho_final.exists():
        raise FileExistsError(f"O arquivo final já existe: {caminho_final}")

    shutil.move(str(caminho_pdf), str(caminho_final))
    return caminho_final

def processar_zip_relatorio(caminho_zip, matricula, nome, competencia, local, data_desligamento):
    """
    Função principal que orquestra a localização das pastas dinâmicas,
    extração do ZIP e a movimentação final do arquivo de ponto.
    """
    # Usamos a nova função que calcula a rota com base na data do evento
    caminho_base = montar_caminho_base_desligamento(
        local=local,
        data_desligamento=data_desligamento
    )

    pasta_colaborador = localizar_pasta_colaborador(
        caminho_base=caminho_base,
        matricula=matricula
    )

    pasta_espelho = obter_pasta_espelho_ponto(pasta_colaborador=pasta_colaborador)
    pasta_extraida = extrair_zip(caminho_zip=caminho_zip)
    caminho_pdf = localizar_pdf_extraido(pasta_extraida=pasta_extraida)

    caminho_final = mover_pdf_para_pasta_espelho(
        caminho_pdf=caminho_pdf,
        pasta_espelho=pasta_espelho,
        matricula=matricula,
        nome=nome,
        competencia=competencia
    )

    return caminho_final