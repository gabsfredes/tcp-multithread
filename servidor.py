import socket
import sqlite3
import os
import time
import json
import gzip
from multiprocessing import Process, Manager

# Configurações
DB_PATH = 'basecpf.db'
LIMITE_PROCESSOS = 5
LIMITE_RESULTADOS = 20

def consultar_banco(comando_sql, parametros=()):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(comando_sql, parametros)
        resultados = cursor.fetchall()
        colunas = [descricao[0] for descricao in cursor.description]
        conn.close()
        return colunas, resultados
    except Exception as e:
        return None, f"Erro ao consultar o banco: {e}"

def enviar_pacote(cliente_socket, mensagem_obj):
    try:
        mensagem_json = json.dumps(mensagem_obj)
        mensagem_bytes = mensagem_json.encode('utf-8')
        mensagem_compactada = gzip.compress(mensagem_bytes)

        tamanho = len(mensagem_compactada)
        cliente_socket.sendall(tamanho.to_bytes(4, byteorder='big') + mensagem_compactada)
    except Exception as e:
        print(f"❌ Erro ao enviar pacote: {e}")

def receber_pacote(cliente_socket):
    try:
        tamanho_bytes = cliente_socket.recv(4)
        if not tamanho_bytes:
            return None
        tamanho = int.from_bytes(tamanho_bytes, byteorder='big')
        dados_compactados = cliente_socket.recv(tamanho)
        dados_json = gzip.decompress(dados_compactados).decode('utf-8')
        mensagem = json.loads(dados_json)
        return mensagem
    except Exception as e:
        print(f"❌ Erro ao receber pacote: {e}")
        return None

def tratar_consulta(cliente_socket, mensagem, endereco):
    try:
        start_time = time.time()

        tipo = mensagem.get("tipo")
        valor = mensagem.get("valor")
        request_id = mensagem.get("request_id")

        if tipo == "nome":
            comando_sql = f"SELECT * FROM cpf WHERE nome LIKE ? LIMIT {LIMITE_RESULTADOS};"
        elif tipo == "cpf":
            comando_sql = "SELECT * FROM cpf WHERE cpf = ?;"
        else:
            enviar_pacote(cliente_socket, {"erro": "Tipo de consulta inválido.", "request_id": request_id})
            print(f"❌ Enviando erro para {endereco} (tipo inválido)")
            return

        colunas, resultados = consultar_banco(comando_sql, (valor,))
        if colunas:
            resposta = {
                "colunas": colunas,
                "dados": resultados,
                "request_id": request_id
            }
        else:
            resposta = {
                "erro": "Nenhum resultado encontrado.",
                "request_id": request_id
            }

        enviar_pacote(cliente_socket, resposta)

        tempo_total = time.time() - start_time

        if "erro" in resposta:
            print(f"📤 Enviado para {endereco}: ERRO ({resposta['erro']}) [Tempo: {tempo_total:.2f}s]\n")
        else:
            print(f"📤 Enviado para {endereco}: {len(resposta['dados'])} registros retornados na consulta por {tipo}. [Tempo: {tempo_total:.2f}s]\n")

    except Exception as e:
        print(f"❌ Erro ao processar consulta para {endereco}: {e}")


def tratar_cliente(cliente_socket, endereco, consultas_ativas):
    print(f"🖧 Cliente conectado: {endereco}")

    processos_consultas = []
    LIMITE_CONSULTAS_POR_CLIENTE = 5

    while True:
        mensagem = receber_pacote(cliente_socket)
        if not mensagem:
            print(f"🖧 Cliente {endereco} desconectou.")
            break

        # 🔥 Agora sim: logamos IMEDIATAMENTE ao receber
        print(f"🖧 Pedido recebido de {endereco}: {mensagem}")

        # 🔥 Atualizar a lista de processos vivos
        processos_consultas = [p for p in processos_consultas if p.is_alive()]

        if len(processos_consultas) >= LIMITE_CONSULTAS_POR_CLIENTE:
            request_id = mensagem.get("request_id")
            resposta = {
                "erro": f"Limite de {LIMITE_CONSULTAS_POR_CLIENTE} consultas simultâneas atingido. Aguarde terminar.",
                "request_id": request_id
            }
            enviar_pacote(cliente_socket, resposta)
            print(f"⚠️ Consulta recusada para {endereco} (limite atingido)\n")
            continue

        # 🔥 Disparar a consulta em subprocesso separado
        processo_consulta = Process(target=tratar_consulta, args=(cliente_socket, mensagem, endereco))
        processo_consulta.start()
        processos_consultas.append(processo_consulta)

    cliente_socket.close()





def iniciar_servidor_socket():
    ip = input("Informe o IP para o servidor escutar (ex: 0.0.0.0): ").strip()
    porta = int(input("Informe a Porta para o servidor escutar (ex: 5000): ").strip())

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind((ip, porta))
    servidor.listen()
    servidor.settimeout(1)  # 🔥 timeout para poder verificar input 'sair' no loop
    print(f"\n🖧 Servidor socket escutando em {ip}:{porta}...\n")

    with Manager() as manager:
        consultas_ativas = manager.list()

        print("Digite 'sair' para encerrar o servidor.")
        while True:
            try:
                # Primeiro tenta aceitar conexões
                try:
                    cliente, endereco = servidor.accept()
                    processo_cliente = Process(target=tratar_cliente, args=(cliente, endereco, consultas_ativas))
                    processo_cliente.start()
                except socket.timeout:
                    pass  # Sem conexão, seguimos

                # Agora verifica se o admin digitou 'sair'
                if os.name == 'nt':
                    # Windows
                    import msvcrt
                    if msvcrt.kbhit():
                        comando = input()
                        if comando.strip().lower() == 'sair':
                            raise KeyboardInterrupt
                else:
                    # Linux / Unix
                    import select, sys
                    dr, dw, de = select.select([sys.stdin], [], [], 0)
                    if dr:
                        comando = sys.stdin.readline()
                        if comando.strip().lower() == 'sair':
                            raise KeyboardInterrupt

            except KeyboardInterrupt:
                print("\nEncerrando servidor socket...")
                servidor.close()
                break


if __name__ == '__main__':
    from multiprocessing import set_start_method
    try:
        set_start_method('spawn')
    except RuntimeError:
        pass

    iniciar_servidor_socket()
