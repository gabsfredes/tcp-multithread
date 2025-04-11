# servidor.py
import socket
import sqlite3
import json
import time

HOST = '127.0.0.1'
PORT = 5000
DB_PATH = 'basecpf.db'

def consultar_banco(comando_sql):
    try:
        inicio = time.time()  # ⏱️ Início da medição

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(comando_sql)
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        conn.close()

        fim = time.time()  # ⏱️ Fim da medição
        tempo_execucao = fim - inicio

        return {
            "status": "ok",
            "colunas": colunas,
            "resultados": resultados,
            "tempo_execucao_segundos": round(tempo_execucao, 6)
        }

    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

def iniciar_servidor():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind((HOST, PORT))
        servidor.listen()
        print(f"Servidor escutando em {HOST}:{PORT}")

        while True:
            conexao, endereco = servidor.accept()
            with conexao:
                print(f"Conexão estabelecida com {endereco}")
                dados = conexao.recv(4096)

                if not dados:
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

if __name__ == '__main__':
    iniciar_servidor()
