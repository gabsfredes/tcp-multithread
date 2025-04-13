import socket
import json
import threading

def enviar_mensagens(cliente):
    while True:
        print("\nEscolha uma opção de busca:")
        print("1. Buscar por nome")
        print("2. Buscar por CPF")
        print("3. Sair")
        opcao = input("Informe a opção desejada (1, 2 ou 3): ").strip()

        if opcao == '3':
            print("⛔ Encerrando conexão com o servidor.")
            cliente.close()
            break

        if opcao == '1':
            nome = input("Informe o nome para busca: ").strip()
            if not nome:
                print("⚠️ Nome não pode ser vazio.")
                continue
            comando_sql = f"SELECT * FROM cpf WHERE nome LIKE '%{nome}%'"
        elif opcao == '2':
            cpf = input("Informe o CPF para busca: ").strip()
            if not cpf:
                print("⚠️ CPF não pode ser vazio.")
                continue
            comando_sql = f"SELECT * FROM cpf WHERE cpf = '{cpf}'"
        else:
            print("⚠️ Opção inválida. Tente novamente.")
            continue

        payload = {"sql": comando_sql}
        cliente.sendall(json.dumps(payload).encode('utf-8'))


def receber_respostas(cliente):
    while True:
        try:
            resposta = cliente.recv(4096)
            if not resposta:
                print("❌ Conexão encerrada pelo servidor.")
                break

            resposta_json = json.loads(resposta.decode('utf-8'))
            if resposta_json['status'] == 'ok':
                colunas = resposta_json['colunas']
                resultados = resposta_json['resultados']
                tempo = resposta_json.get('tempo_execucao_segundos', 0)

                print("\nResultado:")
                print(" | ".join(colunas))
                for linha in resultados:
                    print(" | ".join(str(val) for val in linha))

                print(f"\nTempo de execução: {tempo:.6f} segundos\n")
            else:
                print("Erro:", resposta_json.get('mensagem'))
        except Exception as e:
            print(f"❌ Erro ao receber dados do servidor: {e}")
            break

def enviar_sql():
    host = input("Informe o IP do servidor (ex: 127.0.0.1): ").strip()
    try:
        porta = int(input("Informe a porta do servidor (ex: 5000): ").strip())
    except ValueError:
        print("Porta inválida.")
        return

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
            cliente.connect((host, porta))
            print("✅ Conectado com sucesso!\n")

            # Criar threads para envio e recebimento
            thread_envio = threading.Thread(target=enviar_mensagens, args=(cliente,))
            thread_recebimento = threading.Thread(target=receber_respostas, args=(cliente,))

            thread_envio.start()
            thread_recebimento.start()

            # Esperar as threads terminarem
            thread_envio.join()
            thread_recebimento.join()

    except Exception as e:
        print(f"❌ Erro ao conectar ou comunicar com o servidor: {e}")

if __name__ == '__main__':
    enviar_sql()
