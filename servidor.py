import sys
import socket
import sqlite3
import json
import time
import os
import threading
from multiprocessing import Process, Queue, set_start_method, Manager
import ssl
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog
from servidor_gui import Ui_Servidor



def consultar_nome_processo(db_path, valor, limite_resultados, queue_resultado):
    print(f"[PROCESSO filho] PID do subprocesso: {os.getpid()}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM cpf WHERE nome LIKE ? LIMIT {limite_resultados};", (valor,))
    resultados = cursor.fetchall()
    colunas = [desc[0] for desc in cursor.description]
    conn.close()
    queue_resultado.put((colunas, resultados))
    
def consultar_cpf(db_path, valor):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cpf WHERE cpf = ?;", (valor,))
    resultados = cursor.fetchall()
    colunas = [desc[0] for desc in cursor.description]
    conn.close()
    return colunas, resultados


class ServidorWindow(QtWidgets.QMainWindow, Ui_Servidor):
    
    def get_db_path(self):
        return getattr(self, "caminho_banco", None)
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        self.max_processos = self.campo_processos.value()
        self.processos_ativos = 0

        self.botao_iniciar.clicked.connect(self.iniciar_servidor)
        self.botao_desligar.clicked.connect(self.parar_servidor)
        self.botao_escolher_banco.clicked.connect(self.selecionar_banco)
        self.botao_limpar_terminal.clicked.connect(self.limpar_terminal)

        self.servidor_socket = None
        self.servidor_thread = None
        self.servidor_rodando = False
        self.mensagem_queue = Queue()

        self.clientes_ativos = []

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.checar_mensagens_queue)
        self.timer.start(100)

        self.atualizar_led_status(False)

    def log(self, mensagem):
        self.terminal_informacoes.append(mensagem)
        self.terminal_informacoes.ensureCursorVisible()

    def checar_mensagens_queue(self):
        while not self.mensagem_queue.empty():
            msg = self.mensagem_queue.get()
            self.log(msg)

    def selecionar_banco(self):
        options = QFileDialog.Options()
        arquivo, _ = QFileDialog.getOpenFileName(self, "Selecionar Banco de Dados", "", "Banco de Dados (*.db);;Todos os Arquivos (*)", options=options)
        if arquivo:
            self.label_banco.setText(f"Banco selecionado")
            self.caminho_banco = arquivo
            self.log(f"📄 Banco: {arquivo}")

    def iniciar_servidor(self):
        if self.servidor_rodando:
            self.log("⚠️ Servidor já está rodando.")
            return

        try:
            ip_texto = self.campo_ip.text().strip()
            porta_texto = self.campo_porta.text().strip()

            if not ip_texto or not porta_texto:
                self.log("❌ IP e Porta precisam ser preenchidos antes de iniciar o servidor.")
                return

            self.ip = ip_texto
            self.porta = int(porta_texto)

            self.max_processos = self.campo_processos.value()
            self.limite_clientes = int(self.spinbox_maxclientes.value())
            self.limite_resultados = int(self.campo_resultados.value())
            self.db_path = getattr(self, "caminho_banco", None)

            if not self.db_path:
                self.log("❌ Selecione um banco de dados antes de iniciar.")
                return

            # 🔐 Criar socket e aplicar camada SSL
            socket_base = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_base.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            contexto_ssl = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            contexto_ssl.load_cert_chain(certfile='cert.pem', keyfile='chave.pem')

            self.servidor_socket = contexto_ssl.wrap_socket(socket_base, server_side=True)

            self.servidor_socket.bind((self.ip, self.porta))
            self.servidor_socket.listen(self.limite_clientes)

            self.log(f"🔧 Servidor SSL iniciado em {self.ip}:{self.porta}")
            self.servidor_rodando = True

            # Mantendo o servidor em execução com um único loop contínuo.
            self.servidor_thread = threading.Thread(target=self.aceitar_clientes, daemon=True)
            self.servidor_thread.start()

            self.botao_iniciar.setEnabled(True)
            self.atualizar_led_status(True)

        except Exception as e:
            self.log(f"❌ Erro ao iniciar servidor com SSL: {e}")


        except Exception as e:
            self.log(f"❌ Erro ao iniciar servidor com SSL: {e}")


    def parar_servidor(self):
        if self.servidor_rodando:
            resposta = QtWidgets.QMessageBox.question(
                self,
                'Confirmação',
                'Deseja realmente desligar o servidor?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )

            if resposta == QtWidgets.QMessageBox.No:
                return

            try:
                self.servidor_rodando = False

                if self.servidor_socket:
                    self.servidor_socket.close()

                for cliente_socket, endereco in self.clientes_ativos:
                    try:
                        cliente_socket.shutdown(socket.SHUT_RDWR)
                        cliente_socket.close()
                    except:
                        pass
                self.clientes_ativos[:] = []

                self.log("🛑 Servidor e clientes encerrados com sucesso.")
                self.atualizar_led_status(False)
                self.atualizar_conexoes(0)

                self.botao_iniciar.setEnabled(True)

            except Exception as e:
                self.log(f"❌ Erro ao parar o servidor: {e}")
        else:
            self.log("⚠️ Servidor não está rodando.")

    def limpar_terminal(self):
        self.terminal_informacoes.clear()

    def atualizar_led_status(self, ligado):
        self.status_led.setText("🟢 Ligado" if ligado else "🔴 Desligado")

    def aceitar_clientes(self):
        while self.servidor_rodando:
            try:
                cliente_socket, endereco = self.servidor_socket.accept()

                if len(self.clientes_ativos) >= self.limite_clientes:
                    try:
                        mensagem = {"tipo": "rejeitado", "motivo": "Limite de clientes atingido."}
                        mensagem_json = json.dumps(mensagem).encode('utf-8')
                        tamanho = len(mensagem_json)
                        cliente_socket.sendall(tamanho.to_bytes(4, byteorder='big') + mensagem_json)
                    except Exception as e:
                        self.log(f"⚠️ Erro ao enviar mensagem de rejeição: {e}")
                    finally:
                        cliente_socket.close()
                        self.log(f"⚠️ Conexão recusada de {endereco} (limite de clientes atingido)")

                    continue

                self.clientes_ativos.append(cliente_socket)
                self.log(f"📢 Cliente conectado: {endereco}")

                self.tratar_cliente(cliente_socket, endereco)

            except Exception as e:
                self.log(f"❌ Erro aceitando cliente: {e}")

    
    def tratar_cliente(self, cliente_socket, endereco):
        def enviar_pacote(cliente_socket, mensagem_obj):
            try:
                mensagem_json = json.dumps(mensagem_obj)
                mensagem_bytes = mensagem_json.encode('utf-8')
                tamanho = len(mensagem_bytes)
                cliente_socket.sendall(tamanho.to_bytes(4, byteorder='big') + mensagem_bytes)
            except Exception as e:
                self.mensagem_queue.put(f"❌ Erro enviando resposta para {endereco}: {e}")

        def receber_pacote(cliente_socket):
            try:
                tamanho_bytes = cliente_socket.recv(4)
                if not tamanho_bytes:
                    return None
                tamanho = int.from_bytes(tamanho_bytes, byteorder='big')
                dados = b''
                while len(dados) < tamanho:
                    dados += cliente_socket.recv(tamanho - len(dados))
                dados_json = dados.decode('utf-8')
                return json.loads(dados_json)
            except:
                return None

        def processar_consulta(tipo, valor, request_id):
            try:
                start_time = time.time()

                if self.processos_ativos >= self.max_processos:
                    mensagem = {"erro": "🚀 Limite de processos atingido. Tente uma nova pesquisa após obter um resultado"}
                    enviar_pacote(cliente_socket, mensagem)
                    return 
            
                if tipo == "nome":
                    self.processos_ativos += 1
                    resultado_queue = Queue()
                    p = Process(target=consultar_nome_processo, args=(self.db_path, valor, self.limite_resultados, resultado_queue))
                    p.start()
                    
                    colunas, resultados = resultado_queue.get()
                    self.processos_ativos -= 1

                elif tipo == "cpf":
                    colunas, resultados = consultar_cpf(self.db_path, valor)
                else:
                    enviar_pacote(cliente_socket, {"erro": "Tipo inválido", "request_id": request_id})
                    self.mensagem_queue.put(f"⚠️ Tipo inválido de {endereco}")
                    return

                tempo_total = time.time() - start_time

                if colunas and resultados:
                    resposta = {"colunas": colunas, "dados": resultados, "request_id": request_id, "tempo": tempo_total}
                else:
                    resposta = {"erro": "Nenhum resultado encontrado.", "request_id": request_id, "tempo": tempo_total}

                enviar_pacote(cliente_socket, resposta)
                self.mensagem_queue.put(f"📤 Resposta enviada para {endereco} (Tempo: {tempo_total:.2f} segundos)")
            except Exception as e:
                self.mensagem_queue.put(f"❌ Erro processando consulta de {endereco}: {e}")

        try:
            while self.servidor_rodando:
                mensagem = receber_pacote(cliente_socket)
                if not mensagem:
                    break

                tipo = mensagem.get("tipo")
                valor = mensagem.get("valor")
                request_id = mensagem.get("request_id")

                self.mensagem_queue.put(f"📢 Pedido recebido de {endereco}: {mensagem}")

                threading.Thread(target=processar_consulta, args=(tipo, valor, request_id), daemon=True).start()

        except Exception as e:
            self.mensagem_queue.put(f"❌ Erro com {endereco}: {e}")
        finally:
            try:
                cliente_socket.close()
            except:
                pass
            if threading.current_thread() is threading.main_thread() or threading.current_thread().name.startswith('Thread'):
                if cliente_socket in self.clientes_ativos:
                    self.clientes_ativos.remove(cliente_socket)
    
if __name__ == "__main__":
    try:
        set_start_method('spawn')
    except RuntimeError:
        pass

    print(f"[MAIN] PID do processo principal: {os.getpid()}")

    app = QtWidgets.QApplication(sys.argv)
    janela = ServidorWindow()
    janela.show()
    sys.exit(app.exec_())
