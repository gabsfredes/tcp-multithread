import socket
import sqlite3
import json
import time
import threading

DB_PATH = 'basecpf.db'
MAX_CONEXOES = 100  # Limite máximo de conexões simultâneas

ENCERRAR = False
conexoes_ativas = 0
lock = threading.Lock()

def consultar_banco(comando_sql):
    """Executa um comando SQL no banco de dados e retorna os resultados."""
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

def lidar_com_cliente(conexao, endereco, log_callback=print):
    """Lida com a comunicação de um cliente conectado."""
    global conexoes_ativas
    log_callback(f"🧵 Cliente conectado: {endereco} (Thread: {threading.current_thread().name})")

    try:
        while True:
            dados = conexao.recv(4096)
            if not dados:
                log_callback(f"❌ Cliente {endereco} desconectado.")
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
        log_callback(f"⚠️ Cliente {endereco} desconectado abruptamente.")

    finally:
        with lock:
            conexoes_ativas -= 1
        conexao.close()

def monitorar_entrada(log_callback=print):
    """Monitora a entrada do terminal para comandos administrativos."""
    global ENCERRAR
    while True:
        comando = input().strip().lower()
        if comando == "sair":
            log_callback("⛔ Encerrando servidor manualmente...")
            ENCERRAR = True
            break

def iniciar_servidor(host, port, log_callback=print, max_clientes=100):
    """
    Inicia o servidor TCP com o IP, porta e máximo de clientes fornecidos.
    As mensagens são redirecionadas para o log_callback.
    """
    global ENCERRAR, conexoes_ativas, MAX_CONEXOES
    MAX_CONEXOES = max_clientes  # Atualiza o limite de conexões

    threading.Thread(target=monitorar_entrada, args=(log_callback,), daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind((host, port))
        servidor.listen()
        servidor.settimeout(1.0)

        log_callback(f"🚀 Servidor escutando em {host}:{port} (máx {MAX_CONEXOES} conexões simultâneas)")

        while not ENCERRAR:
            try:
                conexao, endereco = servidor.accept()
            except socket.timeout:
                continue

            with lock:
                if conexoes_ativas >= MAX_CONEXOES:
                    log_callback(f"❌ Limite de conexões atingido. Rejeitando {endereco}")
                    conexao.sendall(json.dumps({
                        "status": "erro",
                        "mensagem": "Limite de conexões simultâneas atingido"
                    }).encode('utf-8'))
                    conexao.close()
                    continue

                conexoes_ativas += 1

            thread = threading.Thread(target=lidar_com_cliente, args=(conexao, endereco, log_callback), daemon=True)
            thread.start()

        log_callback("🧹 Servidor finalizado.")