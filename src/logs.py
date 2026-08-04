from datetime import datetime

from src.config import PASTA_LOGS


def registrar_ocorrencia(
    tipo,
    matricula,
    nome=None,
    competencia=None,
    detalhes=None,
):
    """
    Registra apenas ocorrências que precisam ser verificadas depois.

    Tipos usados atualmente:
    - PASTA_NAO_ENCONTRADA
    - ARQUIVO_JA_EXISTE
    """

    PASTA_LOGS.mkdir(
        parents=True,
        exist_ok=True,
    )

    data_atual = datetime.now().strftime("%Y-%m-%d")

    caminho_log = (
        PASTA_LOGS
        / f"ocorrencias_{data_atual}.log"
    )

    data_hora = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    partes = [
        data_hora,
        tipo,
        f"matricula={matricula}",
    ]

    if nome:
        partes.append(f"nome={nome}")

    if competencia:
        partes.append(
            f"competencia={competencia}"
        )

    if detalhes:
        partes.append(f"detalhes={detalhes}")

    mensagem = " | ".join(partes) + "\n"

    with open(
        caminho_log,
        mode="a",
        encoding="utf-8",
    ) as arquivo_log:
        arquivo_log.write(mensagem)