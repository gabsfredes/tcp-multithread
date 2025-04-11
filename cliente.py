import socket
import json

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

            while True:
                comando_sql = input("SQL > ").strip()
                if comando_sql.lower() == 'sair':
                    print("⛔ Encerrando conexão com o servidor.")
                    break

                payload = {"sql": comando_sql}
                cliente.sendall(json.dumps(payload).encode('utf-8'))

                resposta = cliente.recv(4096)
                resposta_json = json.loads(resposta.decode('utf-8'))

                if resposta_json['status'] == 'ok':
                    colunas = resposta_json['colunas']
                    resultados = resposta_json['resultados']
                    tempo = resposta_json.get('tempo_execucao_segundos', 0)

                    print(" | ".join(colunas))
                    for linha in resultados:
                        print(" | ".join(str(val) for val in linha))

                    print(f"\nTempo de execução: {tempo:.6f} segundos\n")
                else:
                    print("Erro:", resposta_json.get('mensagem'))

    except Exception as e:
        print(f"❌ Erro ao conectar ou comunicar com o servidor: {e}")

if __name__ == '__main__':
    enviar_sql()
