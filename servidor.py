import sys
import socket
import sqlite3
import json
import gzip
import time
import os

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog
from multiprocessing import Process, Manager, Queue, set_start_method

from servidor_gui import Ui_Servidor  # Ajuste o caminho se necessário

class ServidorWindow(QtWidgets.QMainWindow, Ui_Servidor):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.botao_iniciar.clicked.connect(self.iniciar_servidor)
        self.botao_desligar.clicked.connect(self.parar_servidor)
        self.botao_escolher_banco.clicked.connect(self.selecionar_banco)
        self.botao_limpar_terminal.clicked.connect(self.limpar_terminal)

        self.servidor_socket = None
        self.processos_clientes = []
        self.servidor_rodando = False
        self.mensagem_queue = Queue()

        self.manager = Manager()
        self.clientes_ativos = self.manager.list()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.checar_mensagens_queue)
        self.timer.start(100)

        self.atualizar_led_status(False)
        self.atualizar_conexoes(0)

    def log(self, mensagem):
        self.terminal_informacoes.append(mensagem)
        self.terminal_informacoes.ensureCursorVisible()

    def checar_mensagens_queue(self):
        while not self.mensagem_queue.empty():
            msg = self.mensagem_queue.get()
            if msg.startswith("__update_conexoes__"):
                quantidade = int(msg.split("__update_conexoes__")[1].strip())
                self.atualizar_conexoes(quantidade)
            else:
                self.log(msg)

    def selecionar_banco(self):
        options = QFileDialog.Options()
        arquivo, _ = QFileDialog.getOpenFileName(self, "Selecionar Banco de Dados", "", "Banco de Dados (*.db);;Todos os Arquivos (*)", options=options)
        if arquivo:
            self.label_banco.setText(f"Banco selecionado: {arquivo}")
            self.caminho_banco = arquivo
            self.log(f"📄 Banco selecionado: {arquivo}")

    def iniciar_servidor(self):
        if self.servidor_rodando:
            self.log("⚠️ Servidor já está rodando.")
            return

        try:
            ip_texto = self.campo_ip.text().strip()
            porta_texto = self.campo_porta.text().strip()

            # 🔥 Verificar se IP e Porta foram preenchidos
            if not ip_texto or not porta_texto:
                self.log("❌ IP e Porta precisam ser preenchidos antes de iniciar o servidor.")
                return

            self.ip = ip_texto
            self.porta = int(porta_texto)

            self.limite_clientes = int(self.spinbox_maxclientes.value())
            self.limite_processos = int(self.campo_processos.value())
            self.limite_resultados = int(self.campo_resultados.value())
            self.db_path = getattr(self, "caminho_banco", None)

            if not self.db_path:
                self.log("❌ Selecione um banco de dados antes de iniciar.")
                return

            self.servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.servidor_socket.bind((self.ip, self.porta))
            self.servidor_socket.listen(self.limite_clientes)

            self.log(f"🖧 Servidor iniciado em {self.ip}:{self.porta}")
            self.servidor_rodando = True

            self.servidor_loop = Process(target=self.aceitar_clientes, args=(self.servidor_socket, self.mensagem_queue, self.db_path, self.limite_resultados, self.limite_clientes))
            self.servidor_loop.start()

            self.botao_iniciar.setEnabled(False)  # 🔥 Desabilitar botão após iniciar

            self.atualizar_led_status(True)
            self.atualizar_conexoes(0)

        except Exception as e:
            self.log(f"❌ Erro ao iniciar servidor: {e}")


    def parar_servidor(self):
        if self.servidor_rodando:
            # 🔥 Novo: mostrar popup de confirmação
            resposta = QtWidgets.QMessageBox.question(
                self,
                'Confirmação',
                'Deseja realmente desligar o servidor?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
    
            if resposta == QtWidgets.QMessageBox.No:
                return  # 🔥 Se clicou "Não", não desliga o servidor
    
            try:
                # 🔥 Fecha o socket principal
                self.servidor_socket.close()
    
                # 🔥 Finaliza o processo principal de aceitação
                self.servidor_loop.terminate()
    
                # 🔥 Termina todos os processos de clientes conectados
                for proc in self.processos_clientes:
                    if proc.is_alive():
                        proc.terminate()
    
                self.processos_clientes.clear()
    
                # 🔥 Limpa lista de clientes
                self.clientes_ativos[:] = []
    
                self.servidor_rodando = False
    
                self.log("🛑 Servidor e todos clientes encerrados com sucesso.")
                self.atualizar_led_status(False)
                self.atualizar_conexoes(0)
    
                # 🔥 Reabilitar botão de iniciar
                self.botao_iniciar.setEnabled(True)
    
            except Exception as e:
                self.log(f"❌ Erro ao parar o servidor: {e}")
        else:
            self.log("⚠️ Servidor não está rodando.")
    

    def limpar_terminal(self):
        self.terminal_informacoes.clear()

    def atualizar_led_status(self, ligado):
        if ligado:
            self.status_led.setText("🟢 Ligado")
        else:
            self.status_led.setText("🔴 Desligado")

    def atualizar_conexoes(self, quantidade):
        self.label_conexoes_ativas.setText(f"👥 Conexões ativas: {quantidade}")

    @staticmethod
    def aceitar_clientes(servidor_socket, mensagem_queue, db_path, limite_resultados, limite_clientes):
       clientes_ativos = []
       while True:
           try:
               cliente_socket, endereco = servidor_socket.accept()

               # 🔥 Aqui verificamos antes de aceitar
               if len(clientes_ativos) >= limite_clientes:
                   mensagem_queue.put(f"⚠️ Conexão recusada de {endereco} (limite de clientes atingido)")
                   cliente_socket.close()
                   continue

               clientes_ativos.append(endereco)
               mensagem_queue.put(f"🖧 Cliente conectado: {endereco}")
               mensagem_queue.put(f"__update_conexoes__ {len(clientes_ativos)}")

               processo_cliente = Process(target=ServidorWindow.tratar_cliente, args=(cliente_socket, endereco, mensagem_queue, db_path, limite_resultados, clientes_ativos))
               processo_cliente.start()

           except Exception as e:
               mensagem_queue.put(f"❌ Erro aceitando cliente: {e}")



    @staticmethod
    def tratar_cliente(cliente_socket, endereco, mensagem_queue, db_path, limite_resultados, clientes_ativos):
        try:
            def enviar_pacote(cliente_socket, mensagem_obj):
                mensagem_json = json.dumps(mensagem_obj)
                mensagem_bytes = mensagem_json.encode('utf-8')
                mensagem_compactada = gzip.compress(mensagem_bytes)
                tamanho = len(mensagem_compactada)
                cliente_socket.sendall(tamanho.to_bytes(4, byteorder='big') + mensagem_compactada)
    
            def receber_pacote(cliente_socket):
                tamanho_bytes = cliente_socket.recv(4)
                if not tamanho_bytes:
                    return None
                tamanho = int.from_bytes(tamanho_bytes, byteorder='big')
                dados_compactados = b''
                while len(dados_compactados) < tamanho:
                    dados_compactados += cliente_socket.recv(tamanho - len(dados_compactados))
                dados_json = gzip.decompress(dados_compactados).decode('utf-8')
                return json.loads(dados_json)
    
            def consultar_banco(db_path, comando_sql, parametros=()):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(comando_sql, parametros)
                resultados = cursor.fetchall()
                colunas = [descricao[0] for descricao in cursor.description]
                conn.close()
                return colunas, resultados
    
            while True:
                mensagem = receber_pacote(cliente_socket)
                if not mensagem:
                    clientes_ativos.remove(endereco)
                    mensagem_queue.put(f"🖧 Cliente {endereco} desconectou.")
                    mensagem_queue.put(f"__update_conexoes__ {len(clientes_ativos)}")
                    break
                
                tipo = mensagem.get("tipo")
                valor = mensagem.get("valor")
                request_id = mensagem.get("request_id")
    
                mensagem_queue.put(f"🖧 Pedido recebido de {endereco}: {mensagem}")
    
                if tipo == "nome":
                    comando_sql = f"SELECT * FROM cpf WHERE nome LIKE ? LIMIT {limite_resultados};"
                elif tipo == "cpf":
                    comando_sql = "SELECT * FROM cpf WHERE cpf = ?;"
                else:
                    enviar_pacote(cliente_socket, {"erro": "Tipo inválido", "request_id": request_id})
                    mensagem_queue.put(f"⚠️ Tipo inválido de {endereco}")
                    continue
                
                start_time = time.time()  # ⏱️ Começa a contar o tempo da consulta
                colunas, resultados = consultar_banco(db_path, comando_sql, (valor,))
                tempo_total = time.time() - start_time  # ⏱️ Termina a contagem
    
                if colunas and resultados:
                    resposta = {"colunas": colunas, "dados": resultados, "request_id": request_id}
                    enviar_pacote(cliente_socket, resposta)
                    mensagem_queue.put(
                        f"📤 Resposta enviada para {endereco}: Pesquisa por {tipo.upper()} = '{valor}' - {len(resultados)} registros encontrados. (Tempo: {tempo_total:.2f} segundos)"
                    )
                else:
                    resposta = {"erro": "Nenhum resultado encontrado.", "request_id": request_id}
                    enviar_pacote(cliente_socket, resposta)
                    mensagem_queue.put(
                        f"📤 Resposta enviada para {endereco}: Pesquisa por {tipo.upper()} = '{valor}' - Nenhum resultado encontrado. (Tempo: {tempo_total:.2f} segundos)"
                    )
    
            cliente_socket.close()
    
        except Exception as e:
            mensagem_queue.put(f"❌ Erro com {endereco}: {e}")
    

        except Exception as e:
            mensagem_queue.put(f"❌ Erro com {endereco}: {e}")

if __name__ == "__main__":
    try:
        set_start_method('spawn')
    except RuntimeError:
        pass

    app = QtWidgets.QApplication(sys.argv)
    janela = ServidorWindow()
    janela.show()
    sys.exit(app.exec_())
