
from getpass import getpass
from src.browser import criar_navegador
from src.pontotel import (acessar_login,
                          preencher_email,
                          preencher_senha_entrar,)

def main():
    email = "denise.soares@jtptransportes.com.br"
    senha = "Denny3129@"

    navegador = criar_navegador()

    acessar_login(navegador)
    preencher_email(navegador, email)
    preencher_senha_entrar(navegador, senha)

    input("Pressione ENTER para sair")
    navegador.quit()

if __name__ == "__main__":
    main()

