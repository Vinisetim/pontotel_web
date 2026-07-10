from pathlib import Path

from src.arquivo import processar_zip_relatorio


def main():
    caminho_zip = Path(
        r"C:\Users\vinicius.gomes\Documents\pontotel-automacao\downloads_pontotel\r01-9-2024-wu2ydyevtm.zip"
    )

    caminho_final = processar_zip_relatorio(
        caminho_zip=caminho_zip,
        matricula="1428",
        nome="DIEGO DE OLIVEIRA MENDONCA",
        competencia="2024-10",
        local="COM | Embu das Artes",
        status="Desligado"
    )

    print(f"PDF movido para: {caminho_final}")


if __name__ == "__main__":
    main()