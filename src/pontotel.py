from selenium.webdriver.chrome import webdriver
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from src.arquivo import esperar_novo_zip

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

from datetime import date

def calcular_diferenca(data_inicial, data_final):
    """Calcula a diferença em meses entre duas datas"""
    return (data_final.year - data_inicial.year) * 12 + (data_final.month - data_inicial.month)


def voltar_um_mes(ano, mes):
    """
    Recebe um ano e mês, e retorna o mês anterior.
    """

    if mes == 1:
        return ano - 1, 12

    return ano, mes - 1



def gerar_competencias_do_periodo(admissao, demissao):
    """
    Gera uma lista de competências entre o mês da demissão e o mês da admissão.

    A lista vem em ordem decrescente, porque o site será navegado voltando mês a mês.

    Exemplo:
    admissao = 07/10/2019
    demissao = 14/10/2024

    Retorno:
    [
        "2024-10",
        "2024-09",
        "2024-08",
        ...
        "2019-10"
    ]
    """

    if demissao < admissao:
        raise ValueError("A data de demissão não pode ser anterior à data de admissão.")

    ano_atual = demissao.year
    mes_atual = demissao.month

    ano_limite = admissao.year
    mes_limite = admissao.month

    competencias = []

    while True:
        competencia = f"{ano_atual}-{mes_atual:02d}"
        competencias.append(competencia)

        if ano_atual == ano_limite and mes_atual == mes_limite:
            break

        ano_atual, mes_atual = voltar_um_mes(ano_atual, mes_atual)

    return competencias


def calcular_periodo_relatorios(admissao, demissao):
    """calcula as informações para navegar no Pontotel
    retorna a quantidade de meses até a demissao (que vai ser o número de cliques para voltar)
    competencia: lista de meses que devem ter relatorio gerado
    """

    data_atual = date.today()

    meses_ate_demissao = calcular_diferenca(demissao, data_atual)

    if meses_ate_demissao < 0:
        raise ValueError("A data de demissão está no futuro em relação ao mês atual.")

    competencias = gerar_competencias_do_periodo(admissao, demissao)

    return {
        "meses_ate_demissao": meses_ate_demissao,
        "competencias": competencias,
        "quantidade_relatorios": len(competencias),
    }

def voltar_meses(navegador, quantidade_meses):
    """
    Clica no botão de voltar mes do pontotel N vezes
    """

    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)

    for numero_clique in range(quantidade_meses):
        botao_mes_anterior = wait.until(
            EC.element_to_be_clickable(
                (
                By.XPATH,
                "//*[@aria-label='Mês anterior']"
                 )
            )
        )

        botao_mes_anterior.click()
        print(f"Voltando mês: {numero_clique + 1} de {quantidade_meses}")

        time.sleep(1)


def gerar_relatorio_mes_atual(navegador):
    """Gerar relatórios do mes atualmente selecionado no pontotel"""

    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)

    botao_gerar_folha = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//*[@aria-label='gerar folha/espelho de ponto']"
        )
    )
)

    botao_gerar_folha.click()

    botao_gerar = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[.//span[normalize-space()='Gerar']]"

            )
        )
    )

    botao_gerar.click()

    botao_ok = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[normalize-space()='OK']"
            )
        )
    )

    botao_ok.click()

def gerar_relatorios_periodo(navegador, competencias):
    """Gera relatórios mes a mes, partindo do mes de demissao até o mes de admissao"""
    total_competencias = len(competencias)

    for indice, competencia in enumerate(competencias):
        print(f"Gerando relatório da competencia: {competencia} ({indice + 1}/{total_competencias})")

        gerar_relatorio_mes_atual(navegador)

        time.sleep(1)

        ultima_competencia = indice == total_competencias - 1

        if not ultima_competencia:
            voltar_meses(navegador, 1)
            time.sleep(1)


def baixar_relatorio_competencia(
    navegador,
    posicao,
    arquivos_antes
):
    """
    Abre a gaveta, inicia o download quando necessário,
    espera o ZIP terminar e fecha a gaveta.

    Regras:
    - posição 0: abrir a gaveta inicia o download automático;
    - posição maior que 0: é necessário clicar no botão de download;
    - a gaveta só fecha depois que o ZIP terminar de baixar.
    """

    wait = WebDriverWait(
        navegador,
        TEMPO_ESPERA_PADRAO
    )

    print("Abrindo gaveta de relatórios...")

    botao_gaveta = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//li[@id='secao-alertas']//button"
            )
        )
    )

    navegador.execute_script(
        "arguments[0].click();",
        botao_gaveta
    )

    print("Aguardando relatório ficar disponível...")

    botao_download = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "(//*[contains(@aria-label, 'Baixar relatório')])[1]"
            )
        )
    )

    print("Relatório mais recente disponível.")

    if posicao == 0:
        print(
            "Primeira competência: "
            "aguardando download automático."
        )

    else:
        print(
            "Clicando no download do relatório mais recente..."
        )

        navegador.execute_script(
            "arguments[0].click();",
            botao_download
        )

        print("Clique no download executado.")

    caminho_zip = esperar_novo_zip(arquivos_antes)

    print(f"ZIP concluído: {caminho_zip}")
    print("Fechando gaveta...")

    botao_fechar = wait.until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "button[aria-label='Fechar gaveta']"
            )
        )
    )

    navegador.execute_script(
        "arguments[0].click();",
        botao_fechar
    )

    time.sleep(1)

    print("Clique para fechar a gaveta executado.")

    return caminho_zip