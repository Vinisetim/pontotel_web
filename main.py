from src.browser import criar_navegador
from src.controle import validar_colunas, ler_planilha
from src.pontotel import (acessar_login,
                          preencher_email,
                          preencher_senha_entrar,
                          clicar_folha,
                          buscar_empregado,
                          calcular_periodo_relatorios,
                          voltar_meses,
                          gerar_relatorios_periodo)

def main():
    email = "denise.soares@jtptransportes.com.br"
    senha = "Denny3129@"

    df = ler_planilha()
    validar_colunas(df)

    navegador = criar_navegador()

    acessar_login(navegador)
    preencher_email(navegador, email)
    preencher_senha_entrar(navegador, senha)
    clicar_folha(navegador)

    for indice, linha in df.iterrows():
        matricula = str(linha["MATRICULA"]).strip()
        nome = str(linha["NOME DO AUTOR"]).strip()
        admissao = linha["ADMISSAO"]
        demissao = linha["DEMISSAO"]
        periodo = calcular_periodo_relatorios(admissao, demissao)

        print(f"Meses até a demissão: {periodo['meses_ate_demissao']}")
        print(f"Quantidade de relatórios: {periodo['quantidade_relatorios']}")
        print(f"Primeira competência: {periodo['competencias'][0]}")
        print(f"Última competência: {periodo['competencias'][-1]}")

        buscar_empregado(navegador, matricula)

        voltar_meses(navegador, periodo['meses_ate_demissao'])
        gerar_relatorios_periodo(navegador, periodo['competencias'])

        input("Pressione ENTER para sair")

    navegador.quit()

if __name__ == "__main__":
    main()

