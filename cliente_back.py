import socket
import json
import gzip
import threading
import os
import uuid
import time

consultas_pendentes = {}

def enviar_pacote(sock, mensagem_obj):
    try:
        mensagem_json = json.dumps(mensagem_obj)
        mensagem_bytes = mensagem_json.encode('utf-8')
        mensagem_compactada = gzip.compress(mensagem_bytes)

        tamanho = len(mensagem_compactada)
        sock.sendall(tamanho.to_bytes(4, byteorder='big') + mensagem_compactada)
    except Exception as e:
        print(f"❌ Erro ao enviar pacote: {e}")

def receber_pacote(sock):
    try:
        tamanho_bytes = sock.recv(4)
        if not tamanho_bytes:
            return None
        tamanho = int.from_bytes(tamanho_bytes, byteorder='big')
        dados_compactados = b''
        while len(dados_compactados) < tamanho:
            dados_compactados += sock.recv(tamanho - len(dados_compactados))
        dados_json = gzip.decompress(dados_compactados).decode('utf-8')
        mensagem = json.loads(dados_json)
        return mensagem
    except Exception as e:
        print(f"❌ Erro ao receber pacote: {e}")
        return None

def thread_envio(cliente):
    while True:
        print("\nEscolha uma opção de consulta:")
        print("1. Consultar por Nome")
        print("2. Consultar por CPF")
        print("Digite 'sair' para encerrar.")

        opcao = input("Opção > ").strip()
        if opcao.lower() == 'sair':
            print("Encerrando cliente...")
            cliente.close()
            os._exit(0)
            break

        if opcao == '1':
            nome = input("Informe o Nome (use % para buscas parciais): ").strip()
            request_id = str(uuid.uuid4())
            mensagem = {
                "tipo": "nome",
                "valor": nome,
                "request_id": request_id
            }
            consultas_pendentes[request_id] = {
                "descricao": f"Consulta por Nome: {nome}",
                "inicio": time.time()
            }
        elif opcao == '2':
            cpf = input("Informe o CPF: ").strip()
            request_id = str(uuid.uuid4())
            mensagem = {
                "tipo": "cpf",
                "valor": cpf,
                "request_id": request_id
            }
            consultas_pendentes[request_id] = {
                "descricao": f"Consulta por CPF: {cpf}",
                "inicio": time.time()
            }
        else:
            print("Opção inválida. Tente novamente.")
            continue

        enviar_pacote(cliente, mensagem)

def thread_recebimento(cliente):
    while True:
        resposta = receber_pacote(cliente)

        if resposta is None:
            print("❌ Conexão encerrada pelo servidor.")
            os._exit(0)
            break

        request_id = resposta.get("request_id")
        consulta_info = consultas_pendentes.pop(request_id, {"descricao": "Consulta desconhecida", "inicio": time.time()})

        tempo_total = time.time() - consulta_info["inicio"]

        if "erro" in resposta:
            print(f"\n❌ {consulta_info['descricao']} - Erro: {resposta['erro']} (Tempo: {tempo_total:.2f}s)")
        else:
            if not resposta['dados']:  # 🔥 Se lista vazia
                print(f"\n⚠️ {consulta_info['descricao']} - Nenhum resultado encontrado. (Tempo: {tempo_total:.2f}s)")
            else:
                print(f"\n📋 Resultado de {consulta_info['descricao']} (Tempo: {tempo_total:.2f}s):")
                print(" | ".join(resposta['colunas']))
                for linha in resposta['dados']:
                    print(" | ".join(str(valor) for valor in linha))
        print("\n(Aguardando nova ação...)\n")


def conectar_ao_servidor():
    ip = input("Informe o IP do servidor: ").strip()
    porta = int(input("Informe a Porta do servidor: ").strip())

    try:
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((ip, porta))
        print(f"✅ Conectado ao servidor {ip}:{porta}\n")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return

    threading.Thread(target=thread_envio, args=(cliente,), daemon=True).start()
    threading.Thread(target=thread_recebimento, args=(cliente,), daemon=True).start()

    while True:
        pass

if __name__ == '__main__':
    conectar_ao_servidor()
