import socket
import sqlite3
import json
import time
import threading

HOST = '127.0.0.1'
PORT = 5000
DB_PATH = 'basecpf.db'

ENCERRAR = False  # Flag global para encerrar o servidor

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

def monitorar_entrada():
    global ENCERRAR
    while True:
        comando = input().strip().lower()
        if comando == "sair":
            print("⛔ Encerrando servidor manualmente...")
            ENCERRAR = True
            break

def iniciar_servidor():
    global ENCERRAR

    threading.Thread(target=monitorar_entrada, daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind((HOST, PORT))
        servidor.listen()
        servidor.settimeout(1.0)  # timeout curto para checar a flag ENCERRAR
        print(f"Servidor escutando em {HOST}:{PORT} (digite 'sair' para encerrar)")

        while not ENCERRAR:
            try:
                conexao, endereco = servidor.accept()
            except socket.timeout:
                continue  # volta e checa se ENCERRAR foi acionado

            print(f"✅ Conexão estabelecida com {endereco}")
            with conexao:
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

        print("🧹 Servidor finalizado.")

if __name__ == '__main__':
    iniciar_servidor()
