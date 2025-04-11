# cliente.py
import socket
import json

HOST = '127.0.0.1'
PORT = 5000

def enviar_sql():
    while True:
        comando_sql = input("SQL > ").strip()
        if comando_sql.lower() == 'sair':
            break

        payload = {"sql": comando_sql}

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
            cliente.connect((HOST, PORT))
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

                print(f"\nTempo de execução: {tempo:.6f} segundos")
            else:
                print("Erro:", resposta_json.get('mensagem'))


if __name__ == '__main__':
    enviar_sql()
