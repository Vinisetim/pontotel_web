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

# Mapeamento EXATO das unidades (Padrão: NEGÓCIO | UNIDADE)
MAPA_UNIDADES = {
    "ESCOLAR | BRAGANÇA PAULISTA": "braganca_paulista_escolar",
    "ESCOLAR | BARUERI": "barueri_escolar",
    "ESCOLAR | EMBU DAS ARTES": "embu_das_artes_escolar",
    "ESCOLAR | EMBU": "embu_das_artes_escolar",  # Variação curta
    "ESCOLAR | EMBU GUAÇU": "embu_guacu_escolar",
    "ESCOLAR | ITAPECERICA DA SERRA": "itapecerica_da_serra_escolar",
    "ESCOLAR | OSASCO": "osasco_escolar",
    "COM | EMBU DAS ARTES": "embu_das_artes_coletivo",
    "COM | EMBU": "embu_das_artes_coletivo",  # Variação curta
    "COM | BRAGANÇA PAULISTA": "braganca_paulista_coletivo",
    "COM | PORTO VELHO": "porto_velho_coletivo"
}


def normalzar_nome_arquivo(texto):
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")
    texto = re.sub(r'[\\/:*?"<>|]', "", texto)
    texto = re.sub(r"\s+", "_", texto)
    texto = re.sub(r"_+", "_", texto)
    return texto.strip("_")


def limpar_nome_pasta(texto):
    """Limpa o nome removendo caracteres inválidos para diretórios, mas preserva os espaços."""
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")
    texto = re.sub(r'[\\/:*?"<>|]', "", texto)
    return texto.strip()


def obter_arquivos_atuais_download():
    return set(PASTA_DOWNLOADS.glob("*"))


def esperar_arquivo_estavel(caminho_arquivo, timeout=60, intervalo=1):
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
            raise TimeoutError(f"Arquivo não estabilizou: {caminho_arquivo}")
        time.sleep(intervalo)


def esperar_novo_zip(arquivos_antes, timeout=TEMPO_ESPERA_DOWNLOAD, matricula=None, nome=None, competencia=None):
    tempo_inicial = time.time()
    extensoes_temporarias = {".crdownload", ".part", ".tmp"}
    ultima_mensagem = 0
    while True:
        arquivos_agora = set(PASTA_DOWNLOADS.glob("*"))
        arquivos_novos = arquivos_agora - arquivos_antes

        arquivos_temporarios = [arq for arq in arquivos_novos if arq.suffix.lower() in extensoes_temporarias]
        arquivos_zip_novos = [arq for arq in arquivos_novos if arq.suffix.lower() == ".zip"]
        arquivos_nao_zip = [arq for arq in arquivos_novos if
                            arq.suffix.lower() not in extensoes_temporarias and arq.suffix.lower() != ".zip"]

        if arquivos_temporarios:
            if time.time() - ultima_mensagem >= 30:
                print("Download ainda em andamento...")
                ultima_mensagem = time.time()
            if timeout is not None and time.time() - tempo_inicial > timeout:
                raise TimeoutError("Tempo excedido aguardando o download temporário.")
            time.sleep(2)
            continue

        if arquivos_zip_novos:
            zip_baixado = max(arquivos_zip_novos, key=lambda arquivo: arquivo.stat().st_mtime)
            esperar_arquivo_estavel(zip_baixado)
            return zip_baixado

        if arquivos_nao_zip:
            arquivo_invalido = max(arquivos_nao_zip, key=lambda arquivo: arquivo.stat().st_mtime)
            esperar_arquivo_estavel(arquivo_invalido)
            mensagem_erro = f"Arquivo baixado não é ZIP: {arquivo_invalido}"
            registrar_ocorrencia("ARQUIVO_BAIXADO_NAO_ZIP", matricula=matricula, nome=nome, competencia=competencia,
                                 detalhes=mensagem_erro)
            raise FileNotFoundError(mensagem_erro)

        if timeout is not None and time.time() - tempo_inicial > timeout:
            raise TimeoutError("Tempo excedido esperando um novo arquivo ZIP.")

        time.sleep(2)


def limpar_pasta_processamento():
    if PASTA_PROCESSAMENTO.exists():
        shutil.rmtree(PASTA_PROCESSAMENTO)
    PASTA_PROCESSAMENTO.mkdir(parents=True, exist_ok=True)


def extrair_zip(caminho_zip):
    limpar_pasta_processamento()
    with zipfile.ZipFile(caminho_zip, "r") as arquivo_zip:
        arquivo_zip.extractall(PASTA_PROCESSAMENTO)
    return PASTA_PROCESSAMENTO


def localizar_pdf_extraido(pasta_extraida):
    arquivos_pdf = list(Path(pasta_extraida).rglob("*.pdf"))
    if not arquivos_pdf:
        raise FileNotFoundError("Nenhum arquivo PDF dentro do zip")
    if len(arquivos_pdf) > 1:
        raise ValueError("Mais de 1 PDF encontrado dentro do zip")
    return arquivos_pdf[0]


def obter_pasta_unidade(local_csv):
    """Mapeia a coluna do CSV diretamente para a pasta da unidade correspondente."""
    # O .upper() garante que independentemente de vir 'com' ou 'COM', será comparado em maiúsculo
    # O re.sub padroniza qualquer espaçamento estranho ao redor da barra vertical (pipe)
    local_limpo = re.sub(r'\s*\|\s*', ' | ', str(local_csv).upper().strip())

    if "MATRIZ" in local_limpo:
        return "Matriz"

    pasta = MAPA_UNIDADES.get(local_limpo)

    # Fallback de segurança ignorando acentuação (ex: 'GUACU' vs 'GUAÇU')
    if not pasta:
        local_sem_acento = unicodedata.normalize('NFKD', local_limpo).encode('ASCII', 'ignore').decode('ASCII')
        for key, value in MAPA_UNIDADES.items():
            key_sem_acento = unicodedata.normalize('NFKD', key).encode('ASCII', 'ignore').decode('ASCII')
            if key_sem_acento == local_sem_acento:
                return value
        raise ValueError(f"Unidade não mapeada no dicionário: '{local_csv}'")

    return pasta


def montar_caminho_base_desligamento(local, data_desligamento):
    """Monta a nova estrutura dinâmica: raiz / unidade / ano(YYYY) / mes(MM) / desligados"""
    pasta_unidade = obter_pasta_unidade(local)
    ano = data_desligamento.strftime("%Y")
    mes = data_desligamento.strftime("%m")

    return PASTA_SHAREPOINT_ARQUIVO / pasta_unidade / ano / mes / "desligados"


def localizar_pasta_colaborador(caminho_base, matricula, nome):
    """Busca a pasta do colaborador. Se não for encontrada (ex: cortes pré-2022), cria a estrutura completa."""
    matricula = str(matricula).strip()
    matricula_formatada = matricula.zfill(6)
    padrao_busca = f"{matricula_formatada}*"

    pastas_encontradas = [caminho for caminho in caminho_base.glob(padrao_busca) if caminho.is_dir()]

    if pastas_encontradas:
        if len(pastas_encontradas) > 1:
            raise ValueError(f"Múltiplas pastas encontradas para {matricula}: {pastas_encontradas}")
        return pastas_encontradas[0]

    # Criação Autónoma: se o caminho ou a pasta não existir, cria a árvore de pastas
    nome_limpo = limpar_nome_pasta(nome)
    nome_pasta_nova = f"{matricula_formatada} - {nome_limpo}"
    nova_pasta = caminho_base / nome_pasta_nova

    nova_pasta.mkdir(parents=True, exist_ok=True)
    print(f"Estrutura ausente detectada. Nova árvore de diretórios criada: {nova_pasta}")

    return nova_pasta


def obter_pasta_espelho_ponto(pasta_colaborador):
    pasta_espelho = pasta_colaborador / "Espelho de Ponto Pontotel"
    pasta_espelho.mkdir(parents=True, exist_ok=True)
    return pasta_espelho


def mover_pdf_para_pasta_espelho(caminho_pdf, pasta_espelho, matricula, nome, competencia):
    nome_arquivo_final = f"{competencia}.pdf"
    caminho_final = pasta_espelho / nome_arquivo_final

    if caminho_final.exists():
        raise FileExistsError(f"O arquivo final já existe: {caminho_final}")

    shutil.move(str(caminho_pdf), str(caminho_final))
    return caminho_final


def processar_zip_relatorio(caminho_zip, matricula, nome, competencia, local, data_desligamento):
    caminho_base = montar_caminho_base_desligamento(
        local=local,
        data_desligamento=data_desligamento
    )

    pasta_colaborador = localizar_pasta_colaborador(
        caminho_base=caminho_base,
        matricula=matricula,
        nome=nome
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