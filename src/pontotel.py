import time
from datetime import date

from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from src.config import URL_PONTOTEL, TEMPO_ESPERA_PADRAO, TEMPO_ESPERA_DOWNLOAD
from src.arquivo import esperar_novo_zip
from src.logs import registrar_ocorrencia


def acessar_login(navegador):
    """Acessa a tela inicial de login do pontotel."""
    navegador.get(URL_PONTOTEL)


def preencher_email(navegador, email):
    """Preenche o campo e-mail e clica no botão próximo"""
    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)
    campo_email = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "input"))
    )
    campo_email.clear()
    campo_email.send_keys(email)

    botao_proximo = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Próximo')]"))
    )
    botao_proximo.click()


def preencher_senha_entrar(navegador, senha):
    """Preenche o campo senha do pontotel e em seguida clica em entrar"""
    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)
    campo_senha = wait.until(
        EC.visibility_of_element_located((By.ID, "password"))
    )
    campo_senha.clear()
    campo_senha.send_keys(senha)

    botao_entrar = wait.until(
        EC.element_to_be_clickable((By.ID, "kc-login"))
    )
    botao_entrar.click()


def entrar_empregados(navegador):
    """Acessa Cadastros > Empregados e abre o filtro que inicialmente está configurado como 'somente ativos'."""
    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)
    print("Abrindo a seção Cadastros...")

    botao_cadastros = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//li[@id='secao-cadastro']//button"))
    )
    botao_cadastros.click()
    time.sleep(1)

    print("Seção Cadastros aberta. Acessando Empregados...")
    link_empregados = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//li[@id='item-empregados']/a"))
    )
    link_empregados.click()
    time.sleep(1)

    print("Aguardando a página de empregados carregar...")
    filtro_empregados = wait.until(
        EC.element_to_be_clickable((By.XPATH, "// label[.// span[normalize-space() = 'mostrar']]"))
    )
    filtro_empregados.click()
    print("Filtro 'somente ativos' aberto.")
    filtro_empregados.click()

    print("Menu suspenso do filtro aberto.")
    opcao_todos = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//div[@role='option' and @title='todos']"))
    )
    opcao_todos.click()
    print("Opção 'todos' selecionada.")
    time.sleep(2)


def buscar_empregados(navegador, matricula):
    """Busca o empregado na página Cadastros > Empregados, abre o painel e clica na folha."""
    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)
    matricula = str(matricula).strip()

    print(f"Buscando empregado pela matrícula {matricula}...")
    time.sleep(2)

    campo_empregado = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class, 'group') and .//label[normalize-space()='empregado']]//input")
        )
    )
    campo_empregado.click()
    campo_empregado.clear()

    if len(matricula) == 3:
        campo_empregado.send_keys("0" + matricula)
    else:
        campo_empregado.send_keys(matricula)

    print("Matrícula digitada. Aguardando o resultado carregar...")
    time.sleep(1)

    try:
        if len(matricula) == 3:
            linha_empregado = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//span[@title and starts-with(normalize-space(@title), '0{matricula} ')]")
                )
            )
        else:
            linha_empregado = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//span[@title and starts-with(normalize-space(@title), '{matricula} ')]")
                )
            )
        linha_empregado.click()
    except TimeoutException as erro:
        registrar_ocorrencia("EMPREGADO_NAO_ENCONTRADO", matricula, detalhes=str(erro))
        raise ValueError(f"Não foi possível encontrar a matrícula {matricula} na tela de busca.")

    time.sleep(1)
    print("Painel lateral aberto. Localizando o botão de folha...")

    botao_folha = wait.until(
        EC.presence_of_element_located((By.XPATH, "//button[.//span[contains(@class, 'icone-chapado-folha')]]"))
    )

    navegador.execute_script(
        """
        arguments[0].scrollIntoView({
            behavior: 'instant',
            block: 'center'
        });
        """,
        botao_folha
    )
    time.sleep(1)

    print("Clicando no botão verde de folha...")
    navegador.execute_script("arguments[0].click();", botao_folha)
    print("Botão de folha acionado.")


def calcular_diferenca(data_inicial, data_final):
    """Calcula a diferença em meses entre duas datas"""
    return (data_final.year - data_inicial.year) * 12 + (data_final.month - data_inicial.month)


def voltar_um_mes(ano, mes):
    """Recebe um ano e mês, e retorna o mês anterior."""
    if mes == 1:
        return ano - 1, 12
    return ano, mes - 1


def gerar_competencias_do_periodo(admissao, demissao):
    """Gera uma lista de competências entre o mês da demissão e o mês da admissão."""
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
    """Calcula as informações para navegar no Pontotel e gerar as competências."""
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
    Clica no botão de voltar mes N vezes.
    Usa a visibilidade/invisibilidade do menu da tabela como âncora para não clicar rápido demais.
    """
    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)
    xpath_ancora = "//a[@title='Opções da linha']"

    for numero_clique in range(quantidade_meses):
        try:
            elemento_antigo = navegador.find_element(By.XPATH, xpath_ancora)
        except NoSuchElementException:
            elemento_antigo = None

        time.sleep(0.5)

        botao_mes_anterior = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//*[@aria-label='Mês anterior']"))
        )
        botao_mes_anterior.click()
        print(f"Voltando mês: {numero_clique + 1} de {quantidade_meses}")

        if elemento_antigo:
            try:
                wait.until(EC.staleness_of(elemento_antigo))
            except TimeoutException:
                pass

        wait.until(EC.visibility_of_element_located((By.XPATH, xpath_ancora)))
        time.sleep(0.5)


def gerar_relatorio_mes_atual(navegador):
    """Gera relatórios do mês atualmente selecionado"""
    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)

    xpath_ancora = "//a[@title='Opções da linha']"
    wait.until(EC.visibility_of_element_located((By.XPATH, xpath_ancora)))

    botao_gerar_folha = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//div[@aria-label='gerar folha/espelho de ponto' "
                "and contains(concat(' ', normalize-space(@class), ' '), ' botao-toolbox ') "
                "and contains(concat(' ', normalize-space(@class), ' '), ' icone-chapado-folha ')]"
            )
        )
    )
    time.sleep(0.5)
    botao_gerar_folha.click()

    botao_gerar = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space()='Gerar']]"))
    )
    time.sleep(1)
    botao_gerar.click()

    botao_ok = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='OK']"))
    )
    time.sleep(0.5)
    botao_ok.click()


def abrir_gaveta_relatorios(navegador):
    """Abre a gaveta lateral de relatórios."""
    time.sleep(0.5)
    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)

    botao_gaveta = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//li[@id='secao-alertas']//button"))
    )
    navegador.execute_script("arguments[0].click();", botao_gaveta)
    print("Gaveta de relatórios aberta.")


def baixar_relatorio_competencia(navegador, posicao, competencia, arquivos_antes, matricula, nome):
    """Lida com a extração visual e download do ZIP da gaveta de relatórios."""
    time.sleep(0.5)
    wait_relatorio = WebDriverWait(
        navegador,
        240,
        poll_frequency=0.5,
        ignored_exceptions=(StaleElementReferenceException, NoSuchElementException)
    )

    seletor_notificacao_sucesso = "#ptt-notifications .alert-success[role='alert'] strong"

    print("Abrindo gaveta de relatórios...")
    abrir_gaveta_relatorios(navegador)
    print("Gaveta de relatórios aberta.")

    print("Aguardando notificação verde de relatório concluído...")

    def notificacao_relatorio_concluido(driver):
        try:
            notificacoes = driver.find_elements(By.CSS_SELECTOR, seletor_notificacao_sucesso)
            for notificacao in notificacoes:
                if notificacao.is_displayed():
                    print("Notificação de conclusão encontrada:", notificacao.text.strip())
                    return True
            return False
        except StaleElementReferenceException:
            return False

    try:
        wait_relatorio.until(notificacao_relatorio_concluido)
    except TimeoutException as erro:
        raise TimeoutException(
            "A notificação verde de relatório concluído não apareceu dentro do tempo esperado.") from erro
    print("Notificação verde detectada. O relatório foi concluído.")

    if posicao == 0:
        print("Primeira competência: mantendo comportamento de download automático após abertura da gaveta.")
    else:
        print("Buscando o primeiro relatório da lista de concluídos...")
        xpath_primeiro_relatorio = "(//div[contains(concat(' ', normalize-space(@class), ' '), ' relatorio ')])[1]"

        def obter_download_primeiro_relatorio(driver):
            try:
                primeiro_relatorio = driver.find_element(By.XPATH, xpath_primeiro_relatorio)
                ActionChains(driver).move_to_element(primeiro_relatorio).pause(0.5).perform()
                botoes_download = primeiro_relatorio.find_elements(By.XPATH,
                                                                   ".//*[contains(@aria-label, 'Baixar relatório')]")

                for botao_download in botoes_download:
                    if botao_download.get_attribute("aria-label"):
                        return botao_download
                return False
            except (StaleElementReferenceException, NoSuchElementException):
                return False

        time.sleep(1)

        def clicar_download_primeiro_relatorio(driver):
            try:
                botao_download = obter_download_primeiro_relatorio(driver)
                if not botao_download: return False
                botao_download = obter_download_primeiro_relatorio(driver)
                if not botao_download: return False

                print("Baixando primeiro relatório da lista:", botao_download.get_attribute("aria-label"))
                driver.execute_script("arguments[0].click();", botao_download)
                return True
            except (StaleElementReferenceException, NoSuchElementException):
                return False

        try:
            WebDriverWait(navegador, TEMPO_ESPERA_DOWNLOAD, poll_frequency=0.5,
                          ignored_exceptions=(StaleElementReferenceException, NoSuchElementException)).until(
                clicar_download_primeiro_relatorio)
        except TimeoutException as erro:
            raise TimeoutException("Não foi possível clicar no download do primeiro relatório da lista.") from erro
        print("Clique no download do primeiro relatório executado.")

    print("Aguardando o arquivo ZIP terminar de baixar...")
    caminho_zip = esperar_novo_zip(arquivos_antes=arquivos_antes, matricula=matricula, nome=nome,
                                   competencia=competencia)
    print(f"ZIP concluído: {caminho_zip}")

    print("Tentando fechar a gaveta de relatórios...")

    def fechar_gaveta_robusta(driver):
        seletor_gaveta = "pontotel-menu-vertical-gaveta-lateral"

        try:
            botoes_x = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Fechar gaveta']")
            for botao in botoes_x:
                if botao.is_displayed():
                    driver.execute_script("arguments[0].click();", botao)
                    break
            WebDriverWait(driver, 3).until(EC.invisibility_of_element_located((By.TAG_NAME, seletor_gaveta)))
            print("Gaveta fechada no botão X.")
            time.sleep(0.5)
            return True
        except Exception:
            pass

        print("X falhou. Tentando tecla ESC...")
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            WebDriverWait(driver, 3).until(EC.invisibility_of_element_located((By.TAG_NAME, seletor_gaveta)))
            print("Gaveta fechada no Plano B (tecla ESC).")
            time.sleep(0.5)
            return True
        except Exception:
            pass

        print("Removendo a gaveta da tela com JavaScript...")
        try:
            driver.execute_script(
                """
                var gavetas = document.getElementsByTagName('pontotel-menu-vertical-gaveta-lateral');
                for(var i = 0; i < gavetas.length; i++) {
                    gavetas[i].style.display = 'none';
                }
                """
            )
            time.sleep(0.5)
            print("Gaveta ocultada.")
            return True
        except Exception as erro:
            print(f"Erro inesperado no fechamento da gaveta: {erro}")
            registrar_ocorrencia("FALHA_AO_FECHAR_GAVETA", matricula, nome, competencia, str(erro))
            return False

    fechou = fechar_gaveta_robusta(navegador)
    if not fechou:
        print("Aviso: não foi possível fechar a gaveta de nenhuma forma. O fluxo tentará continuar.")

    return caminho_zip


def cancelar_relatorio_em_andamento(navegador):
    """
    Cancela o primeiro relatório em andamento se existir para não sobrepor requisições.
    """
    time.sleep(0.5)
    print("Abrindo gaveta de relatórios para verificar itens em andamento...")
    abrir_gaveta_relatorios(navegador)

    wait = WebDriverWait(navegador, 10)
    xpath_botao = "//pontotel-botao[@aria-label='Cancelar geração do relatório']"

    try:
        botao_cancelar = wait.until(
            EC.presence_of_element_located((By.XPATH, xpath_botao))
        )
        print("Botão de cancelamento encontrado. Injetando clique com JavaScript...")
        navegador.execute_script("arguments[0].click();", botao_cancelar)

        botao_ok = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@class, 'swal2-confirm') and normalize-space()='OK']")
            )
        )
        time.sleep(0.5)
        botao_ok.click()
        print("Relatório em andamento cancelado com sucesso.")
        return True

    except TimeoutException:
        print("Nenhum relatório em andamento cancelável foi encontrado.")
        return False
    except Exception as e:
        registrar_ocorrencia("ERRO_CANCELAR_RELATORIO", matricula="N/A", detalhes=str(e))
        return False