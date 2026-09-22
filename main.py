import time

from src.browser import criar_navegador
from src.logs import registrar_ocorrencia
from src.controle import preparar_fila_execucao, salvar_estado_no_blob
from src.pontotel import (
    acessar_login,
    preencher_email,
    preencher_senha_entrar,
    calcular_periodo_relatorios,
    voltar_meses,
    gerar_relatorio_mes_atual,
    baixar_relatorio_competencia,
    buscar_empregados,
    entrar_empregados,
    cancelar_relatorio_em_andamento
)
from src.arquivo import (
    obter_arquivos_atuais_download,
    processar_zip_relatorio,
)


def processar_linha(linha, indice):
    """Processa uma única linha do DataFrame da fila de execução."""
    email = "denise.soares@jtptransportes.com.br"
    senha = "Denny3129@"

    # Consumindo as colunas que foram normalizadas no controle.py
    matricula = str(linha["MATRICULA"]).strip()
    nome = str(linha["NOME"]).strip()
    admissao = linha["ADMISSAO"]
    demissao = linha["DEMISSAO"]  # O controle.py já definiu se é a data real ou a ultima competência
    local = str(linha["LOCAL"]).strip()

    print("=" * 80)
    print(f"Iniciando linha {indice} (Prioridade {linha['PRIORIDADE_PESO']})")
    print(f"Matrícula: {matricula} | Nome: {nome}")
    print(f"Ponto de Partida: {demissao.strftime('%m/%Y')} | Admissão: {admissao.strftime('%m/%Y')}")
    print("=" * 80)

    navegador = criar_navegador()
    ultima_competencia_processada = None

    try:
        acessar_login(navegador)
        preencher_email(navegador, email)
        preencher_senha_entrar(navegador, senha)
        cancelar_relatorio_em_andamento(navegador)
        entrar_empregados(navegador)

        periodo = calcular_periodo_relatorios(admissao=admissao, demissao=demissao)

        print(f"Meses a retroceder: {periodo['meses_ate_demissao']}")
        print(f"Quantidade de relatórios: {periodo['quantidade_relatorios']}")

        buscar_empregados(navegador, matricula)

        voltar_meses(navegador, quantidade_meses=periodo["meses_ate_demissao"])

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
                competencia=competencia,
                arquivos_antes=arquivos_antes,
                matricula=matricula,
                nome=nome,
            )

            try:
                caminho_pdf_final = processar_zip_relatorio(
                    caminho_zip=caminho_zip,
                    matricula=matricula,
                    nome=nome,
                    competencia=competencia,
                    local=local,
                    status='2_Desligados'
                )
                print(f"PDF final salvo em: {caminho_pdf_final}")

            except FileExistsError as erro:
                registrar_ocorrencia("ARQUIVO_JA_EXISTE", matricula, nome, competencia, str(erro))
                print(f"O PDF {competencia} já existe. Registrado no log do Azure.")
            except Exception as erro:
                registrar_ocorrencia("ERRO_AO_MOVER_PDF", matricula, nome, competencia, str(erro))
                raise erro

            ultima_competencia_processada = competencia

            eh_ultima_competencia = posicao == total_competencias - 1
            if not eh_ultima_competencia:
                voltar_meses(navegador, 1)

        print(f"Linha {indice} (Matrícula: {matricula}) finalizada com sucesso de ponta a ponta.")
        return "CONCLUIDO", ultima_competencia_processada

    except Exception as erro_geral:
        print(f"Ocorreu um erro no processamento do {matricula}. Fluxo interrompido nesta linha.")
        registrar_ocorrencia("ERRO_NA_EXECUCAO", matricula, nome, detalhes=str(erro_geral))
        return "EM ANDAMENTO", (ultima_competencia_processada or demissao)

    finally:
        navegador.quit()
        print(f"Navegador fechado para a linha {indice}.")


def main():
    print("Preparando fila de execução com Azure...")
    df_fila = preparar_fila_execucao()

    if df_fila.empty:
        print("Nenhum colaborador pendente na fila. Automação finalizada.")
        return

    print(f"Total de colaboradores na fila de execução: {len(df_fila)}")

    for indice, linha in df_fila.iterrows():
        try:
            novo_status, ultima_competencia = processar_linha(linha, indice)

            df_fila.at[indice, 'STATUS'] = novo_status
            df_fila.at[indice, 'ULTIMA_COMPETENCIA'] = ultima_competencia

            print(f"Salvando checkpoint da matrícula {linha['MATRICULA']} no Azure Blob...")
            df_para_salvar = df_fila[['MATRICULA', 'STATUS', 'ULTIMA_COMPETENCIA']]
            salvar_estado_no_blob(df_para_salvar)

        except Exception as e:
            print(f"Erro fatal não tratado no loop principal: {e}")

    print("Processamento total finalizado.")


if __name__ == "__main__":
    main()