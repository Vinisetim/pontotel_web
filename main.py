import time

from src.browser import criar_navegador
from src.logs import registrar_ocorrencia
from src.controle import preparar_fila_execucao
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
    Controla o login, geração de relatórios e salva a posição de parada em caso de erro.
    """
    email = "denise.soares@jtptransportes.com.br"
    senha = "Denny3129@"

    matricula = str(linha["MATRICULA"]).strip()
    nome = str(linha["NOME"]).strip()
    admissao = linha["ADMISSAO"]

    # Esta data sofre alteração durante o andamento (retrocede a cada mês feito)
    demissao_ponto_partida = linha["DEMISSAO"]

    # Esta é a data original real em que a pessoa foi demitida (usada para achar a pasta)
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

        # O cálculo do período de navegação no site continua usando o ponto de partida dinâmico
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
                # O arquivo.py recebe a data real para criar a rota /2026/09/desligados/
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
                print(f"O PDF {competencia} já existe. Registrado no log do Azure.")
            except Exception as erro:
                registrar_ocorrencia("ERRO_AO_MOVER_PDF", matricula, nome, competencia, str(erro))
                raise erro

            # Registra que este mês foi um sucesso
            ultima_competencia_processada = competencia

            eh_ultima_competencia = posicao == total_competencias - 1
            if not eh_ultima_competencia:
                voltar_meses(navegador, 1)

        print(f"Linha {indice} (Matrícula: {matricula}) finalizada com sucesso de ponta a ponta.")
        return "CONCLUIDO", ultima_competencia_processada

    except Exception as erro_geral:
        print(f"Ocorreu um erro no processamento do {matricula}. Fluxo interrompido nesta linha.")
        registrar_ocorrencia("ERRO_NA_EXECUCAO", matricula, nome, detalhes=str(erro_geral))

        # O bloco abaixo é o que impede o erro "Invalid value for dtype 'str'".
        # Se nenhuma competência foi feita (erro ao logar ou buscar funcionário),
        # formatamos a data do Pandas (Timestamp) para texto (AAAA-MM) antes de salvar no CSV.
        fallback_competencia = demissao_ponto_partida.strftime('%Y-%m')

        return "EM ANDAMENTO", (ultima_competencia_processada or fallback_competencia)

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
            novo_status, ultima_competencia = processar_linha(linha, indice)

            # Usa a nova função que escreve no CSV Mestre local
            from src.controle import atualizar_log_local
            print(f"Atualizando CSV local para a matrícula {linha['MATRICULA']}...")
            atualizar_log_local(linha['MATRICULA'], novo_status, ultima_competencia)

        except Exception as e:
            print(f"Erro fatal não tratado no loop principal: {e}")

    # Ao terminar o loop completo, ele roda uma última vez a sincronização
    # para não precisar esperar o dia seguinte para atualizar a nuvem.
    from src.controle import sincronizar_log_local_com_nuvem
    print("Enviando resultado final da execução de hoje para o Azure...")
    sincronizar_log_local_com_nuvem()

    print("Processamento total finalizado.")

if __name__ == "__main__":
    main()