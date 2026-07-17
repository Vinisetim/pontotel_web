from selenium.webdriver.chrome import webdriver
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from config import TEMPO_ESPERA_DOWNLOAD
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

def entrar_empregados(navegador):
    """
    Acessa Cadastros > Empregados e abre o filtro
    que inicialmente está configurado como 'somente ativos'.

    Esta função ainda não seleciona a opção 'todos'.
    """

    wait = WebDriverWait(
        navegador,
        TEMPO_ESPERA_PADRAO
    )

    print("Abrindo a seção Cadastros...")

    botao_cadastros = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//li[@id='secao-cadastro']//button"
            )
        )
    )

    botao_cadastros.click()

    print("Seção Cadastros aberta.")
    print("Acessando Empregados...")

    link_empregados = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//li[@id='item-empregados']/a"
            )
        )
    )

    link_empregados.click()

    print("Aguardando a página de empregados carregar...")
    filtro_empregados = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//span[contains(@class, 'multiselect__single') "
                "and normalize-space()='somente ativos']"
            )
        )
    )

    filtro_empregados.click()
    print("Menu suspenso do filtro aberto.")

    ActionChains(navegador) \
        .send_keys(Keys.ARROW_DOWN) \
        .send_keys(Keys.ENTER) \
        .perform()

    print("Opção 'todos' selecionada.")


def buscar_empregados(navegador, matricula):
    """
    Busca o empregado na página Cadastros > Empregados,
    abre o painel lateral do colaborador e clica no botão
    verde de folha.

    Pré-condição:
    - a função entrar_empregados() já foi executada;
    - o filtro da página já está configurado como "todos".
    """

    wait = WebDriverWait(
        navegador,
        TEMPO_ESPERA_PADRAO
    )

    matricula = str(matricula).strip()

    print(f"Buscando empregado pela matrícula {matricula}...")

    # Localiza o input da coluna "empregado".
    campo_empregado = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//div[contains(@class, 'group') "
                "and .//label[normalize-space()='empregado']]"
                "//input"
            )
        )
    )

    campo_empregado.click()
    campo_empregado.clear()
    campo_empregado.send_keys(matricula)

    print("Matrícula digitada. Aguardando o resultado carregar...")

    # O title contém matrícula + nome.
    # Exemplo: title="1428 Diego De Oliveira Mendonça"
    linha_empregado = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f"//span[@title and "
                f"starts-with(normalize-space(@title), '{matricula} ')]"
            )
        )
    )

    print("Empregado encontrado. Abrindo o painel lateral...")

    linha_empregado.click()

    print("Painel lateral aberto. Localizando o botão de folha...")

    botao_folha = wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//button[.//span[contains(@class, "
                "'icone-chapado-folha')]]"
            )
        )
    )

    # O botão fica na parte inferior do painel.
    # O scrollIntoView movimenta o painel rolável até o botão.
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

    navegador.execute_script(
        "arguments[0].click();",
        botao_folha
    )

    print("Botão de folha acionado.")



def clicar_folha(navegador, matricula):
    """aguarda a tela inicial se carregar e clica no card com o texto 'folha de ponto'"""

    wait = WebDriverWait(navegador, TEMPO_ESPERA_PADRAO)

    card_folha = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH, "//div[normalize-space()='Cadastros']"
            )
        )
    )
    card_folha.click()

    aba_empregados = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "// a[.// div[normalize-space() = 'Empregados']]"
            )
        )
    )

    aba_empregados.click()

    span_mostrar = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH, "//span[contains(normalize-space(), 'somente ativos')]")
        )
    )

    span_mostrar.click()


    campo_ativo = navegador.switch_to.active_element

    campo_ativo.send_keys(Keys.CONTROL, "a")
    campo_ativo.send_keys(Keys.BACKSPACE)

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

def formatar_competencia_para_relatorio(competencia):
    """
    Converte uma competência*no formato AAAA-MM
    para o form*to MM/AAAA usado pelo aria-label.
    Exemplo:
        2025-10 -> 10/2025
    """

    ano, mes = competencia.split("-")
    competencia_formatada = f"{int(mes)}/{ano}"
    return competencia_formatada

def baixar_relatorio_competencia(
    navegador,
    posicao,
    competencia,
    arquivos_antes
):
    """
    Abre a gaveta lateral de relatórios, espera a notificação verde
    de relatório concluído aparecer e baixa o relatório mais recente.

    Estratégia:
    - a gaveta lateral precisa estar aberta para a notificação aparecer;
    - a notificação verde é usada apenas como gatilho;
    - a automação não clica nem interage com a notificação;
    - posição 0: mantém o comportamento de download automático;
    - posição maior que 0: clica no primeiro botão de download da lista;
    - não busca mais por competência no aria-label;
    - não depende mais de 9/2025 versus 09/2025;
    - falha ao fechar a gaveta não encerra o processamento.
    """

    from selenium.common.exceptions import (
        StaleElementReferenceException,
        NoSuchElementException,
        TimeoutException,
    )

    wait_padrao = WebDriverWait(
        navegador,
        TEMPO_ESPERA_PADRAO,
        poll_frequency=0.5,
        ignored_exceptions=(
            StaleElementReferenceException,
            NoSuchElementException,
        ),
    )

    wait_relatorio = WebDriverWait(
        navegador,
        120,
        poll_frequency=0.5,
        ignored_exceptions=(
            StaleElementReferenceException,
            NoSuchElementException,
        ),
    )

    wait_fechar = WebDriverWait(
        navegador,
        10,
        poll_frequency=0.5,
        ignored_exceptions=(
            StaleElementReferenceException,
            NoSuchElementException,
        ),
    )

    xpath_gaveta = (
        "//li[@id='secao-alertas']//button"
    )

    xpath_downloads = (
        "//*[contains(@aria-label, 'Baixar relatório')]"
    )

    seletor_notificacao_sucesso = (
        "#ptt-notifications .alert-success[role='alert'] strong"
    )

    seletor_fechar = (
        "button[aria-label='Fechar gaveta']"
    )

    # ---------------------------------------------------------
    # 1. Abre a gaveta lateral de relatórios
    # ---------------------------------------------------------

    print("Abrindo gaveta de relatórios...")

    def abrir_gaveta(driver):
        try:
            botao_gaveta = driver.find_element(
                By.XPATH,
                xpath_gaveta
            )

            if not (
                botao_gaveta.is_displayed()
                and botao_gaveta.is_enabled()
            ):
                return False

            driver.execute_script(
                "arguments[0].click();",
                botao_gaveta
            )

            return True

        except (
            StaleElementReferenceException,
            NoSuchElementException,
        ):
            return False

    wait_padrao.until(
        abrir_gaveta
    )

    print("Gaveta de relatórios aberta.")

    # ---------------------------------------------------------
    # 2. Espera a notificação verde aparecer
    # ---------------------------------------------------------

    print(
        "Aguardando notificação verde de relatório concluído..."
    )

    def notificacao_relatorio_concluido(driver):
        try:
            notificacoes = driver.find_elements(
                By.CSS_SELECTOR,
                seletor_notificacao_sucesso
            )

            for notificacao in notificacoes:
                try:
                    if not notificacao.is_displayed():
                        continue

                    texto = notificacao.text.strip()

                    if not texto:
                        continue

                    print(
                        "Notificação de conclusão encontrada:",
                        texto
                    )

                    return True

                except StaleElementReferenceException:
                    continue

            return False

        except StaleElementReferenceException:
            return False

    try:
        wait_relatorio.until(
            notificacao_relatorio_concluido
        )

    except TimeoutException as erro:
        raise TimeoutException(
            "A notificação verde de relatório concluído não apareceu "
            "dentro do tempo esperado."
        ) from erro

    print(
        "Notificação verde detectada. O relatório foi concluído."
    )

    # ---------------------------------------------------------
    # 3. Download
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # 3. Download
    # ---------------------------------------------------------

    if posicao == 0:
        print(
            "Primeira competência: mantendo comportamento de "
            "download automático após abertura da gaveta."
        )

    else:
        print(
            "Buscando o primeiro relatório da lista de concluídos "
            "usando a lógica antiga..."
        )

        xpath_primeiro_relatorio = (
            "(//div["
            "contains("
            "concat(' ', normalize-space(@class), ' '), "
            "' relatorio '"
            ")"
            "])[1]"
        )

        def obter_download_primeiro_relatorio(driver):
            """
            Usa a lógica antiga:
            1. localiza a primeira linha de relatório da gaveta;
            2. faz hover na primeira linha;
            3. procura o botão de download dentro dessa linha;
            4. retorna o botão encontrado.

            Como o Pontotel coloca o relatório mais recente no topo
            da lista de concluídos, a primeira linha é o item correto.
            """

            try:
                primeiro_relatorio = driver.find_element(
                    By.XPATH,
                    xpath_primeiro_relatorio
                )

                ActionChains(driver) \
                    .move_to_element(primeiro_relatorio) \
                    .pause(0.5) \
                    .perform()

                botoes_download = primeiro_relatorio.find_elements(
                    By.XPATH,
                    ".//*[contains(@aria-label, 'Baixar relatório')]"
                )

                print(
                    "Quantidade de botões de download na primeira linha:",
                    len(botoes_download)
                )

                if not botoes_download:
                    return False

                for indice, botao_download in enumerate(botoes_download):
                    try:
                        aria_label = botao_download.get_attribute(
                            "aria-label"
                        )

                        print(
                            f"Botão candidato {indice}:",
                            aria_label
                        )

                        if not aria_label:
                            continue

                        return botao_download

                    except StaleElementReferenceException:
                        continue

                return False

            except (
                    StaleElementReferenceException,
                    NoSuchElementException,
            ):
                return False

        def clicar_download_primeiro_relatorio(driver):
            try:
                botao_download = obter_download_primeiro_relatorio(
                    driver
                )

                if not botao_download:
                    return False

                # Rebusca antes do clique, porque o Pontotel pode reconstruir
                # a linha ou o botão depois do hover.
                botao_download = obter_download_primeiro_relatorio(
                    driver
                )

                if not botao_download:
                    return False

                aria_label = botao_download.get_attribute(
                    "aria-label"
                )

                print(
                    "Baixando primeiro relatório da lista:",
                    aria_label
                )

                driver.execute_script(
                    "arguments[0].click();",
                    botao_download
                )

                return True

            except (
                    StaleElementReferenceException,
                    NoSuchElementException,
            ):
                return False

        try:
            WebDriverWait(
                navegador,
                TEMPO_ESPERA_DOWNLOAD,
                poll_frequency=0.5,
                ignored_exceptions=(
                    StaleElementReferenceException,
                    NoSuchElementException,
                ),
            ).until(
                clicar_download_primeiro_relatorio
            )

        except TimeoutException as erro:
            raise TimeoutException(
                "Não foi possível clicar no download do primeiro "
                "relatório da lista usando a lógica antiga."
            ) from erro

        print(
            "Clique no download do primeiro relatório executado."
        )
    # ---------------------------------------------------------
    # 4. Aguarda o ZIP
    # ---------------------------------------------------------

    print(
        "Aguardando o arquivo ZIP terminar de baixar..."
    )

    caminho_zip = esperar_novo_zip(
        arquivos_antes
    )

    print(f"ZIP concluído: {caminho_zip}")

    # ---------------------------------------------------------
    # 5. Fecha a gaveta
    # ---------------------------------------------------------

    print("Tentando fechar a gaveta de relatórios...")

    def clicar_botao_fechar_gaveta(driver):
        """
        Primeira tentativa:
        procura o botão de fechar da gaveta.
        """

        seletores_possiveis = [
            "button[aria-label='Fechar gaveta']",
            "button[aria-label='Fechar']",
            "button[aria-label='Close']",
            "button.close",
        ]

        for seletor in seletores_possiveis:
            try:
                botoes = driver.find_elements(
                    By.CSS_SELECTOR,
                    seletor
                )

                for botao in botoes:
                    try:
                        if (
                            botao.is_displayed()
                            and botao.is_enabled()
                        ):
                            driver.execute_script(
                                "arguments[0].click();",
                                botao
                            )

                            print(
                                "Gaveta fechada pelo botão:",
                                seletor
                            )

                            return True

                    except StaleElementReferenceException:
                        continue

            except StaleElementReferenceException:
                continue

        return False

    def clicar_fora_da_gaveta(driver):
        """
        Segunda tentativa:
        usa o comportamento antigo do seu código,
        clicando em uma área fora da gaveta.
        """

        try:
            elemento_fora_gaveta = driver.execute_script(
                """
                return document.elementFromPoint(
                    Math.floor(window.innerWidth * 0.70),
                    Math.floor(window.innerHeight * 0.50)
                );
                """
            )

            if elemento_fora_gaveta is None:
                return False

            ActionChains(driver) \
                .move_to_element(elemento_fora_gaveta) \
                .click() \
                .perform()

            print(
                "Clique fora da gaveta executado."
            )

            return True

        except (
            StaleElementReferenceException,
            NoSuchElementException,
        ):
            return False

    def fechar_gaveta(driver):
        """
        Tenta fechar a gaveta primeiro pelo botão.
        Se não conseguir, tenta clicar fora dela.
        """

        if clicar_botao_fechar_gaveta(driver):
            return True

        return clicar_fora_da_gaveta(driver)

    try:
        wait_fechar.until(
            fechar_gaveta
        )

        print(
            "Tentativa de fechamento da gaveta executada."
        )

    except TimeoutException:
        print(
            "Aviso: não foi possível fechar a gaveta. "
            "O ZIP já foi baixado e o navegador continuará aberto."
        )

    return caminho_zip