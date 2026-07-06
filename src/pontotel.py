from selenium.webdriver.chrome import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.config import URL_PONTOTEL, TEMPO_ESPERA_PADRAO

def acessar_login(navegador):
    """Acessa a tela inicial de login do pontotel."""
    navegador.get(URL_PONTOTEL)

def preencher_email(navegador, email):
    """Preenche o campo e-mail e clica no botão próximo"""

    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)

    campo_email =   wait.until(
            #essas definições dizem basicamente para aguardar até uma certa condição, no caso é a
            #visibilidade do input
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input"))
    )

    campo_email.clear()
    campo_email.send_keys(email)

    botao_proximo = wait.until(
        #aguarda até o botão ser clicavel
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Próximo')]"))
    )

    botao_proximo.click()

def preencher_senha_entrar(navegador, senha):
    """Preenche o campo senha do pontotel e em seguida clica em entrar"""

    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)

    campo_senha= wait.until(
        EC.visibility_of_element_located((By.ID, "password"))
    )

    campo_senha.clear()
    campo_senha.send_keys(senha)

    botao_entrar = wait.until(
        EC.element_to_be_clickable((By.ID, "kc-login"))
    )

    botao_entrar.click()

def clicar_folha(navegador):
    """aguarda a tela inicial se carregar e clica no card com o texto 'folha de ponto'"""

    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)

    card_folha = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH, "//span[contains(normalize-space(), 'folha de pontos')]"
            )
        )
    )
    card_folha.click()