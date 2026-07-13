from src.browser import criar_navegador
from src.controle import (
    ler_planilha_controle,
    validar_colunas_obrigatorias,
    linha_ja_processada,
    marcar_linha_como_processada,
    salvar_planilha_controle,
)
from src.pontotel import (
    acessar_login,
    preencher_email,
    preencher_senha_entrar,
    clicar_folha,
    buscar_empregado,
    calcular_periodo_relatorios,
    voltar_meses,
    gerar_relatorio_mes_atual,
    baixar_relatorio_competencia
)
from src.arquivo import (
    obter_arquivos_atuais_download,
    esperar_novo_zip,
    processar_zip_relatorio,
)


def processar_linha(linha, indice):
    """
    Processa uma única linha da planilha.

    Para cada linha:
    - abre um navegador novo;
    - faz login;
    - busca o colaborador;
    - gera todos os relatórios do período;
    - processa os ZIPs;
    - move os PDFs finais;
    - fecha o navegador.
    """

    email = "denise.soares@jtptransportes.com.br"
    senha = "Denny3129@"


    matricula = str(linha["MATRICULA"]).strip()
    nome = str(linha["NOME DO AUTOR"]).strip()
    admissao = linha["ADMISSAO"]
    demissao = linha["DEMISSAO"]
    local = str(linha["LOCAL"]).strip()
    status = str(linha["STATUS"]).strip()

    print("=" * 80)
    print(f"Iniciando linha {indice}")
    print(f"Matrícula: {matricula}")
    print(f"Nome: {nome}")
    print(f"Local: {local}")
    print(f"Status: {status}")
    print("=" * 80)

    navegador = criar_navegador()

    try:
        acessar_login(navegador)
        preencher_email(navegador, email)
        preencher_senha_entrar(navegador, senha)
        clicar_folha(navegador)

        periodo = calcular_periodo_relatorios(
            admissao=admissao,
            demissao=demissao,
        )

        print(f"Meses até a demissão: {periodo['meses_ate_demissao']}")
        print(f"Quantidade de relatórios: {periodo['quantidade_relatorios']}")
        print(f"Primeira competência: {periodo['competencias'][0]}")
        print(f"Última competência: {periodo['competencias'][-1]}")

        buscar_empregado(navegador, matricula)

        voltar_meses(
            navegador=navegador,
            quantidade_meses=periodo["meses_ate_demissao"],
        )

        competencias = periodo["competencias"]
        total_competencias = len(competencias)

        for posicao, competencia in enumerate(competencias):
            print("-" * 80)
            print(f"Gerando competência {competencia} ({posicao + 1}/{total_competencias})")

            arquivos_antes = obter_arquivos_atuais_download()

            gerar_relatorio_mes_atual(navegador)

            caminho_zip = baixar_relatorio_competencia(
                navegador=navegador,
                posicao=posicao,
                arquivos_antes=arquivos_antes
            )

            caminho_pdf_final = processar_zip_relatorio(
                caminho_zip=caminho_zip,
                matricula=matricula,
                nome=nome,
                competencia=competencia,
                local=local,
                status=status
            )

            print(f"PDF final salvo em: {caminho_pdf_final}")

            eh_ultima_competencia = posicao == total_competencias - 1

            if not eh_ultima_competencia:
                voltar_meses(navegador, 1)

        print(f"Linha {indice} finalizada com sucesso.")

    finally:
        navegador.quit()
        print(f"Navegador fechado para a linha {indice}.")

def main():
    df = ler_planilha_controle()

    validar_colunas_obrigatorias(df)

    print(f"Quantidade total de linhas na planilha: {len(df)}")

    for indice, linha in df.iterrows():

        if linha_ja_processada(linha):
            print(f"Linha {indice} já está marcada como processada. Pulando.")
            continue

        try:
            processar_linha(linha, indice)

            marcar_linha_como_processada(df, indice)

            salvar_planilha_controle(df)

            print(f"Linha {indice} marcada como processada na planilha.")

        except Exception as erro:
            print("=" * 80)
            print(f"Erro ao processar linha {indice}.")
            print(f"Erro: {erro}")
            print("A linha NÃO será marcada como processada.")
            print("=" * 80)

    print("Processamento finalizado.")


if __name__ == "__main__":
    main()

