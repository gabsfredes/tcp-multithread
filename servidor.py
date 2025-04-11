import socket
import json
import sqlite3

# Configurações
HOST = '127.0.0.1'
PORT = 5000
DB_PATH = 'basecpf.db' 

def consultar_banco(comando_sql):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(comando_sql)
        resultados = cursor.fetchall()
        colunas = [descricao[0] for descricao in cursor.description]
        conn.close()
        return colunas, resultados
    except Exception as e:
        return None, f"Erro ao consultar o banco: {e}"

def iniciar_interface_sql():
    print("Servidor local iniciado. Digite comandos SQL para consultar o banco:")
    print("Digite 'sair' para encerrar.")

    while True:
        comando_sql = input("SQL > ").strip()
        if comando_sql.lower() == 'sair':
            print("Encerrando servidor...")
            break

        if not comando_sql.endswith(';'):
            comando_sql += ';'

        colunas, resultados = consultar_banco(comando_sql)
        if colunas:
            print("→ Resultado da consulta:")
            print(" | ".join(colunas))
            for linha in resultados:
                print(" | ".join(str(valor) for valor in linha))
        else:
            print(resultados)  # mensagem de erro

if __name__ == '__main__':
    iniciar_interface_sql()
