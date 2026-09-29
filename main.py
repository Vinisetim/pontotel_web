import time

from src.browser import criar_navegador
from src.logs import registrar_ocorrencia
from src.controle import (
    preparar_fila_execucao,
    atualizar_log_local,
    sincronizar_log_local_com_nuvem
)
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
    """
    Processa uma única linha do DataFrame da fila de execução.
    Controla o login, geração de relatórios e salva o progresso competência a competência.
    """
    email = "denise.soares@jtptransportes.com.br"
    senha = "Denny3129@"

    matricula = str(linha["MATRICULA"]).strip()
    nome = str(linha["NOME"]).strip()
    admissao = linha["ADMISSAO"]

    demissao_ponto_partida = linha["DEMISSAO"]
    data_desligamento_real = linha["DESLIGAMENTO"]
    local = str(linha["LOCAL"]).strip()

    print("=" * 80)
    print(f"Iniciando linha {indice} (Prioridade {linha['PRIORIDADE_PESO']})")
    print(f"Matrícula: {matricula} | Nome: {nome}")
    print(f"Ponto de Partida: {demissao_ponto_partida.strftime('%m/%Y')} | Admissão: {admissao.strftime('%m/%Y')}")
    print(f"Data Efetiva de Desligamento: {data_desligamento_real.strftime('%d/%m/%Y')}")
    print("=" * 80)

    navegador = criar_navegador()
    ultima_competencia_processada = None

    try:
        acessar_login(navegador)
        preencher_email(navegador, email)
        preencher_senha_entrar(navegador, senha)
        cancelar_relatorio_em_andamento(navegador)
        entrar_empregados(navegador)

        periodo = calcular_periodo_relatorios(admissao=admissao, demissao=demissao_ponto_partida)

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
                    data_desligamento=data_desligamento_real
                )
                print(f"PDF final salvo em: {caminho_pdf_final}")

            except FileExistsError as erro:
                registrar_ocorrencia("ARQUIVO_JA_EXISTE", matricula, nome, competencia, str(erro))
                print(f"O PDF {competencia} já existe. Registrado no log de ocorrências.")
            except Exception as erro:
                registrar_ocorrencia("ERRO_AO_MOVER_PDF", matricula, nome, competencia, str(erro))
                raise erro

            # GRAVAÇÃO AO VIVO: Registra que este mês específico foi um sucesso no log Mestre!
            ultima_competencia_processada = competencia
            atualizar_log_local(matricula, "EM ANDAMENTO", competencia)

            eh_ultima_competencia = posicao == total_competencias - 1
            if not eh_ultima_competencia:
                voltar_meses(navegador, 1)

        print(f"Linha {indice} (Matrícula: {matricula}) finalizada com sucesso de ponta a ponta.")

        # Sela o status final do funcionário como CONCLUIDO
        atualizar_log_local(matricula, "CONCLUIDO", ultima_competencia_processada)
        return "CONCLUIDO", ultima_competencia_processada

    except Exception as erro_geral:
        print(f"Ocorreu um erro no processamento do {matricula}. Fluxo interrompido nesta linha.")
        registrar_ocorrencia("ERRO_NA_EXECUCAO", matricula, nome, detalhes=str(erro_geral))

        fallback_competencia = demissao_ponto_partida.strftime('%Y-%m')
        comp_final = ultima_competencia_processada or fallback_competencia

        # Registra a quebra no log Mestre, salvando a última competência que deu certo
        atualizar_log_local(matricula, "EM ANDAMENTO", comp_final)

        return "EM ANDAMENTO", comp_final

    finally:
        navegador.quit()
        print(f"Navegador fechado para a linha {indice}.")


def main():
    print("Preparando fila de execução e Arquivo Mestre Local...")
    df_fila = preparar_fila_execucao()

    if df_fila.empty:
        print("Nenhum colaborador pendente na fila. Automação finalizada.")
        return

    print(f"Total de colaboradores na fila de execução: {len(df_fila)}")

    for indice, linha in df_fila.iterrows():
        try:
            # A própria função processar_linha já cuida de atualizar o CSV local a cada PDF!
            processar_linha(linha, indice)

            # Ao terminar um funcionário (seja com erro ou sucesso), jogamos o CSV atualizado pro Azure
            print(f"Sincronizando log atualizado do colaborador {linha['MATRICULA']} no Azure Blob...")
            sincronizar_log_local_com_nuvem()

        except Exception as e:
            print(f"Erro fatal não tratado no loop principal: {e}")
            sincronizar_log_local_com_nuvem()

    print("Processamento total finalizado.")


if __name__ == "__main__":
    main()