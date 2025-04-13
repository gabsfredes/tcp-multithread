import socket
import json
import threading

def ouvir_respostas(cliente):
    try:
        while True:
            dados = cliente.recv(8192)
            if not dados:
                print("❌ Conexão encerrada pelo servidor.")
                break

            try:
                resposta = json.loads(dados.decode('utf-8'))
                if resposta["status"] == "ok":
                    print(f"\n📥 Resultado ({resposta['tempo_execucao_segundos']}s):")
                    for linha in resposta["resultados"]:
                        print(dict(zip(resposta["colunas"], linha)))
                else:
                    print(f"⚠️ Erro: {resposta['mensagem']}")
            except json.JSONDecodeError:
                print("⚠️ Resposta do servidor em formato inválido.")

    except Exception as e:
        print(f"❌ Erro ao receber resposta: {e}")
 
def main():
    ip = input("Digite o IP do servidor (padrão 127.0.0.1): ").strip() or "127.0.0.1"
    porta_input = input("Digite a porta do servidor (padrão 5000): ").strip()
    porta = int(porta_input) if porta_input else 5000

    try:
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((ip, porta))
        print(f"✅ Conectado ao servidor {ip}:{porta}")
    except Exception as e:
        print(f"❌ Falha na conexão: {e}")
        return

    threading.Thread(target=ouvir_respostas, args=(cliente,), daemon=True).start()

    print("Digite comandos SQL para enviar ao servidor. Digite 'sair' para encerrar.")
    while True:
        comando = input("SQL > ").strip()
        if comando.lower() == 'sair':
            print("👋 Encerrando cliente...")
            break
        if comando:
            payload = json.dumps({"sql": comando})
            try:
                cliente.sendall(payload.encode('utf-8'))
            except Exception as e:
                print(f"❌ Falha ao enviar comando: {e}")
                break

    cliente.close()

if __name__ == '__main__':
    main()
