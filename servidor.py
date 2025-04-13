import socket
import sqlite3
import json
import time
import threading

HOST = '127.0.0.1'
PORT = 5000
DB_PATH = 'basecpf.db'
MAX_CONEXOES = 100  # Limite máximo de conexões simultâneas

ENCERRAR = False
conexoes_ativas = 0
lock = threading.Lock()

def consultar_banco(comando_sql):
    try:
        inicio = time.time()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(comando_sql)
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        conn.close()
        fim = time.time()
        return {
            "status": "ok",
            "colunas": colunas,
            "resultados": resultados,
            "tempo_execucao_segundos": round(fim - inicio, 6)
        }
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

def lidar_com_cliente(conexao, endereco):
    global conexoes_ativas
    print(f"🧵 Cliente conectado: {endereco} (Thread: {threading.current_thread().name})")

    try:
        while True:
            dados = conexao.recv(4096)
            if not dados:
                print(f"❌ Cliente {endereco} desconectado.")
                break

            try:
                payload = json.loads(dados.decode('utf-8'))
                comando_sql = payload.get("sql")

                if not comando_sql:
                    resposta = {"status": "erro", "mensagem": "Nenhum comando SQL enviado"}
                else:
                    resposta = consultar_banco(comando_sql)

            except json.JSONDecodeError:
                resposta = {"status": "erro", "mensagem": "Formato inválido (esperado JSON)"}

            conexao.sendall(json.dumps(resposta).encode('utf-8'))

    except ConnectionResetError:
        print(f"⚠️ Cliente {endereco} desconectado abruptamente.")

    finally:
        with lock:
            conexoes_ativas -= 1
        conexao.close()

def monitorar_entrada():
    global ENCERRAR
    while True:
        comando = input().strip().lower()
        if comando == "sair":
            print("⛔ Encerrando servidor manualmente...")
            ENCERRAR = True
            break

def iniciar_servidor():
    global ENCERRAR, conexoes_ativas

    threading.Thread(target=monitorar_entrada, daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind((HOST, PORT))
        servidor.listen()
        servidor.settimeout(1.0)

        print(f"🚀 Servidor escutando em {HOST}:{PORT} (máx {MAX_CONEXOES} conexões simultâneas)")

        while not ENCERRAR:
            try:
                conexao, endereco = servidor.accept()
            except socket.timeout:
                continue

            with lock:
                if conexoes_ativas >= MAX_CONEXOES:
                    print(f"❌ Limite de conexões atingido. Rejeitando {endereco}")
                    conexao.sendall(json.dumps({
                        "status": "erro",
                        "mensagem": "Limite de conexões simultâneas atingido"
                    }).encode('utf-8'))
                    conexao.close()
                    continue

                conexoes_ativas += 1

            thread = threading.Thread(target=lidar_com_cliente, args=(conexao, endereco), daemon=True)
            thread.start()

        print("🧹 Servidor finalizado.")

if __name__ == '__main__':
    iniciar_servidor()
