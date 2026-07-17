from src.pontotel import (acessar_login,
                          preencher_email,
                          preencher_senha_entrar,
                          entrar_empregados,
                          buscar_empregados)
from src.browser import criar_navegador

def main():
    navegador = criar_navegador()
    acessar_login(navegador=navegador)
    preencher_email(navegador,email="denise.soares@jtptransportes.com.br")
    preencher_senha_entrar(navegador, senha="Denny3129@")
    entrar_empregados(navegador)
    buscar_empregados(navegador, matricula=1428)
    input("pressione ENTER para sair")
if __name__ == '__main__':
    main()