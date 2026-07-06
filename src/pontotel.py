from selenium.webdriver.chrome import webdriver
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

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

    aba_empregados = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//a[normalize-space() = 'empregados']/ancestor::li"
            )
        )
    )

    aba_empregados.click()

def buscar_empregado(navegador, matricula):
    """
    Busca um empregado na aba 'Empregados' usando o campo MATRICULA

    Fluxo no site:
    1. O campo de empregados já está ativo após clicar na aba empregados.
    2. Digita a matrícula.
    3. O dropdown abre.
    4. A primeira opção é 'todos'.
    5. Pressiona seta para baixo para selecionar o empregado sugerido.
    6. Pressiona Enter.
    7. Clica no botão Buscar.
    """

    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)

    campo_ativo = navegador.switch_to.active_element

    campo_ativo.send_keys(Keys.CONTROL, "a")
    campo_ativo.send_keys(Keys. BACKSPACE)

    campo_ativo.send_keys(matricula)
    time.sleep(5)
    wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//*[contains(normalize-space(), 'todos')]"
            )
        )
    )

    ActionChains(navegador)\
        .send_keys(Keys.ARROW_DOWN)\
        .send_keys(Keys.ENTER)\
        .perform()

    botao_buscar = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH,
             "//button[contains(normalize-space(), 'Buscar')]"
             )
        )
    )
    botao_buscar.click()