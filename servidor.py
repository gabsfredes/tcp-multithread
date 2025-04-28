import socket
import json
import sqlite3
from multiprocessing import Process, Manager
import os
import time

# Configurações
HOST = '127.0.0.1'
PORT = 5000
DB_PATH = 'basecpf.db'
LIMITE_PROCESSOS = 5  # 🔥 Limite máximo de consultas simultâneas

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

def processo_consulta(opcao, valor, consultas_ativas):
    pid = os.getpid() # pegar o PID do processo atual
    print(f"\n[Consulta PID={pid}] Iniciando consulta...")
    start_time = time.time()

    if opcao == '1':
        comando_sql = "SELECT * FROM cpf WHERE nome LIKE ?;"
        colunas, resultados = consultar_banco(comando_sql, (valor,))
    elif opcao == '2':
        comando_sql = "SELECT * FROM cpf WHERE cpf = ?;"
        colunas, resultados = consultar_banco(comando_sql, (valor,))
    else:
        print(f"[Consulta PID={pid}] Opção inválida dentro do processo.")
        consultas_ativas.remove(pid)
        return

    if colunas:
        print(f"[Consulta PID={pid}] Resultado encontrado:")
        print(" | ".join(colunas))
        for linha in resultados:
            print(" | ".join(str(valor) for valor in linha))
    else:
        print(f"[Consulta PID={pid}] {resultados}")

    tempo_gasto = time.time() - start_time
    print(f"[Consulta PID={pid}] Consulta finalizada em {tempo_gasto:.2f} segundos.\n")
    consultas_ativas.remove(pid)
    
def iniciar_interface_sql():
    print("Servidor local iniciado.")
    print("Escolha uma opção para consultar o banco:")
    print("1. Consultar por Nome")
    print("2. Consultar por CPF")
    print("Digite 'sair' para encerrar.")
    print("Digite 'status' para ver consultas ativas.\n")

    with Manager() as manager:
        consultas_ativas = manager.list()

        while True:
            opcao = input("Opção > ").strip()
            if opcao.lower() == 'sair':
                print("Encerrando servidor...")
                break
            elif opcao.lower() == 'status':
                if consultas_ativas:
                    print(f"\nConsultas ativas ({len(consultas_ativas)}):")
                    for pid in consultas_ativas:
                        print(f"- Processo PID {pid}")
                    print()
                else:
                    print("\nNenhuma consulta ativa no momento.\n")
                continue

            # 🔥 Verificar o limite de processos ativos
            if len(consultas_ativas) >= LIMITE_PROCESSOS:
                print("\n⚠️ Muitas consultas ativas no momento. Aguarde alguma consulta terminar!\n")
                continue

            if opcao == '1':
                nome = input("Informe o Nome (use % para buscas parciais): ").strip()
                p = Process(target=processo_consulta, args=(opcao, nome, consultas_ativas))
                p.start()
                consultas_ativas.append(p.pid)
            elif opcao == '2':
                cpf = input("Informe o CPF: ").strip()
                p = Process(target=processo_consulta, args=(opcao, cpf, consultas_ativas))
                p.start()
                consultas_ativas.append(p.pid)
            else:
                print("Opção inválida. Tente novamente.")

if __name__ == '__main__':
    from multiprocessing import set_start_method
    try:
        set_start_method('spawn')  # Melhor para Windows
    except RuntimeError:
        pass
    iniciar_interface_sql()
