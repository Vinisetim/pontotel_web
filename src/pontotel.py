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