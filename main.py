from src.browser import criar_navegador
from src.controle import validar_colunas, ler_planilha
from src.pontotel import (acessar_login,
                          preencher_email,
                          preencher_senha_entrar,
                          clicar_folha,
                          buscar_empregado,)

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

        print(f"Buscando linha {indice}:{matricula} -   {nome}")

        buscar_empregado(navegador, matricula)

        input("Pressione ENTER para sair")

    navegador.quit()

if __name__ == "__main__":
    main()

