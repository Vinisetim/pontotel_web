from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from src.config import PASTA_DOWNLOADS

def criar_navegador():
    """Cria e configura uma instacia de navegador para a automação"""


    PASTA_DOWNLOADS.mkdir(parents=True, exist_ok=True)

    #salva função como variavel
    options = Options()

    #configura comportamentos do navegador antes de abrir (aqui ele configura para abrir maximizado)
    options.add_argument("--start-maximized")

    #variavel com algumas definições em dict
    prefs ={
        #configura diretório do download
        "download.default_directory" : str(PASTA_DOWNLOADS),
        # perguntar onde salvar = False
        "download.prompt_for_directories" : False,
        "download.directory_upgrade" : True,
        # Bloquear notificações
        "profile.default_content_setting_values.notifications" : 2,
        "safebrowsing.enabled" : True,
    }

    options.add_experimental_option("prefs", prefs)

    #baixa ou configura o Chrome automaticamente
    service = Service(ChromeDriverManager().install())

    navegador = webdriver.Chrome(service=service, options=options)

    return navegador