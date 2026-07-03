from src.browser import criar_navegador
from src.config import URL_PONTOTEL
from src.pontotel import acessar_login, preencher_email

def main():
    email = input("Insira o email: ")

    navegador = criar_navegador()

    acessar_login(navegador)
    preencher_email(navegador, email)


    input("Pressione ENTER para sair")
    navegador.quit()

if __name__ == "__main__":
    main()

