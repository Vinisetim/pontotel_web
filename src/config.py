from pathlib import Path

#caminho da raiz
PROJECT_ROOT = Path(__file__).resolve().parent.parent

#caminho das pastas
PASTA_ENTRADA = PROJECT_ROOT / "entrada"
PASTA_OUTPUT = PROJECT_ROOT / "output"
PASTA_PROCESSAMENTO = PROJECT_ROOT / "processamento"
PASTA_LOGS = PROJECT_ROOT / "logs"

#caminho do arquivo da planilha
CAMINHO_PLANILHA_CONTROLE = PASTA_ENTRADA / "controle.xlsx"

#caminho para salvar os downloads
PASTA_DOWNLOADS = Path(r"C:\Users\vinicius.gomes\OneDrive - JTP TRANSPORTES, SERVICOS, GERENCIAMENTO E RECURSOS HUMANOS LTDA\Documentos\pontotel-automacao\downloads_pontotel")

#configurações derais

URL_PONTOTEL = "https://gestao.pontotel.com.br/#/cognito/login"

TEMPO_ESPERA_PADRAO = 20

TEMPO_ESPERA_DOWNLOAD = 120

