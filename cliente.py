import sys
import socket
import threading
import json
import gzip
import os
import uuid
import time
from PyQt5 import QtWidgets, QtCore
from cliente_gui import Ui_Cliente
import ssl


class ClienteWindow(QtWidgets.QMainWindow, Ui_Cliente):
    novo_log = QtCore.pyqtSignal(str)
    novo_alerta = QtCore.pyqtSignal(str, str) 

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.botao_iniciar.clicked.connect(self.conectar_servidor)
        self.botao_nome.clicked.connect(self.pesquisar_nome)
        self.botao_cpf.clicked.connect(self.pesquisar_cpf)
        self.botao_desconectar.clicked.connect(self.desconectar)
        self.botao_limpar_terminal.clicked.connect(self.limpar_terminal)
        

        self.novo_alerta.connect(self._mostrar_alerta_gui)

        self.sock = None
        self.conectado = False
        self.consultas_pendentes = {}

        self.botao_nome.setEnabled(False)
        self.botao_cpf.setEnabled(False)

        self.novo_log.connect(self.terminal_client_area.append)

    def log(self, texto):
        self.novo_log.emit(texto)

    def mostrar_alerta(self, titulo, mensagem):
        alerta = QtWidgets.QMessageBox(self)
        alerta.setIcon(QtWidgets.QMessageBox.Warning)
        alerta.setWindowTitle(titulo)
        alerta.setText(mensagem)
        alerta.setStandardButtons(QtWidgets.QMessageBox.Ok)
        alerta.show()

    def mostrar_alerta(self, titulo, mensagem):
        self.novo_alerta.emit(titulo, mensagem)
        
    def _mostrar_alerta_gui(self, titulo, mensagem):
        alerta = QtWidgets.QMessageBox(self)
        alerta.setIcon(QtWidgets.QMessageBox.Warning)
        alerta.setWindowTitle(titulo)
        alerta.setText(mensagem)
        alerta.setStandardButtons(QtWidgets.QMessageBox.Ok)
        alerta.show()

    def limpar_terminal(self):
        self.terminal_client_area.clear()

    def conectar_servidor(self):

        ip = self.campo_ip.text().strip()
        porta = self.campo_porta.text().strip()

        if not ip or not porta:
            self.log("❌ IP e Porta devem ser preenchidos.")
            return

        try:
            porta = int(porta)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            contexto_ssl = ssl.create_default_context()
            contexto_ssl.load_verify_locations('cert.pem')  # <-- valida contra cert do servidor

            self.sock = contexto_ssl.wrap_socket(sock, server_hostname=ip)
            self.sock.settimeout(5)  # timeout inicial para conexão

            self.sock.connect((ip, porta))
            self.conectado = True

            self.sock.settimeout(1.0)
            try:
                resposta = self.receber_pacote()
                if resposta and resposta.get("tipo") == "rejeitado":
                    motivo = resposta.get("motivo", "Conexão rejeitada.")
                    self.log(f"❌ Conexão rejeitada: {motivo}")
                    self.desconectar(motivo=motivo)
                    return
            except socket.timeout:
                pass
            finally:
                self.sock.settimeout(None)

            self.log(f"✅ Conectado com SSL ao servidor {ip}:{porta}")
            self.log(f"🔐 Protocolo: {self.sock.version()}")
            self.botao_iniciar.setEnabled(False)
            self.botao_nome.setEnabled(True)
            self.botao_cpf.setEnabled(True)

            threading.Thread(target=self.receber_respostas, daemon=True).start()

        except ssl.SSLError as e:
            self.log(f"❌ Erro SSL: {e}")
        except Exception as e:
            self.log(f"❌ Erro ao conectar: {e}")

    def finalizar_conexao(self, sucesso, mensagem):
        try:
            if sucesso:
                ip = self.campo_ip.text().strip()
                porta = int(self.campo_porta.text().strip())
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((ip, porta))
                self.conectado = True

                self.log(f"✅ Conectado ao servidor {ip}:{porta}")

                self.botao_iniciar.setEnabled(False)
                self.botao_nome.setEnabled(True)
                self.botao_cpf.setEnabled(True)

                threading.Thread(target=self.receber_respostas, daemon=True).start()
            else:
                self.log(mensagem)
                self.conectado = False
        finally:
            # 🔥 Encerrando corretamente o thread para não travar
            if self.thread_conexao:
                self.thread_conexao.quit()
                self.thread_conexao.wait()
                self.thread_conexao.deleteLater()
                self.thread_conexao = None

    def desconectar(self, motivo=''):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

        self.conectado = False
        self.botao_iniciar.setEnabled(True)
        self.botao_nome.setEnabled(False)
        self.botao_cpf.setEnabled(False)
        
        if hasattr(self, 'thread_resposta') and self.thread_resposta:
            self.thread_resposta = None

        if motivo:
            self.log(f"🔌 Desconectado: {motivo}")
            self.mostrar_alerta("Desconectado", motivo)
        else:
            self.log("🔌 Desconectado do servidor.")

    def enviar_pacote(self, mensagem_obj):
        if not self.conectado or not self.sock:
            self.log("❌ Não conectado ao servidor. Não é possível enviar a consulta.")
            return

        try:
            mensagem_json = json.dumps(mensagem_obj)
            mensagem_bytes = mensagem_json.encode('utf-8')
            mensagem_compactada = gzip.compress(mensagem_bytes)

            tamanho = len(mensagem_compactada)
            self.sock.sendall(tamanho.to_bytes(4, byteorder='big') + mensagem_compactada)

        except Exception as e:
            self.log(f"❌ Erro ao enviar pacote: {e}")
            self.desconectar(motivo="Erro de envio. Conexão perdida.")

    def receber_pacote(self):
        try:
            tamanho_bytes = self.sock.recv(4)
            if not tamanho_bytes:
                raise ConnectionResetError("Servidor fechou a conexão")
            tamanho = int.from_bytes(tamanho_bytes, byteorder='big')
            dados_compactados = b''
            while len(dados_compactados) < tamanho:
                parte = self.sock.recv(tamanho - len(dados_compactados))
                if not parte:
                    raise ConnectionResetError("Servidor fechou a conexão durante recebimento")
                dados_compactados += parte
            dados_json = gzip.decompress(dados_compactados).decode('utf-8')
            mensagem = json.loads(dados_json)
            return mensagem
        except socket.timeout:
            # Apenas devolver None silenciosamente para timeout (sem log)
            return None
        except Exception as e:
            self.log(f"❌ Erro ao receber pacote: {e}")
            return None
        
    def receber_respostas(self):
        try:
            while self.conectado:
                resposta = self.receber_pacote()
                if resposta is None:
                    break
                
                # 🚨 Novo tratamento
                if resposta.get("tipo") == "rejeitado":
                    motivo = resposta.get("motivo", "Conexão rejeitada pelo servidor.")
                    self.log(f"❌ Conexão rejeitada: {motivo}")
                    self.desconectar(motivo=motivo)
                    break
                
                request_id = resposta.get("request_id")
                tempo_total = resposta.get("tempo", 0.0)
                consulta_info = self.consultas_pendentes.pop(request_id, {"descricao": "Consulta desconhecida", "inicio": time.time()})
    
                if "erro" in resposta:
                    self.log(f"❌ {consulta_info['descricao']} - Erro: {resposta['erro']} (Tempo: {tempo_total:.2f}s)")
                else:
                    if not resposta['dados']:
                        self.log(f"⚠️ {consulta_info['descricao']} - Nenhum resultado encontrado. (Tempo: {tempo_total:.2f}s)")
                    else:
                        resultado_texto = f"📋 Resultado de {consulta_info['descricao']} (Tempo: {tempo_total:.2f}s):\n"
                        resultado_texto += " | ".join(resposta['colunas']) + "\n"
                        for linha in resposta['dados']:
                            resultado_texto += " | ".join(str(valor) for valor in linha) + "\n"
                        self.log(resultado_texto)
        except OSError as e:
            if e.winerror == 10053:
                self.log("🔌 Conexão encerrada normalmente.")
            else:
                self.log(f"❌ Erro na thread de respostas: {e}")
        except Exception as e:
            self.log(f"❌ Erro inesperado na thread de respostas: {e}")
        finally:
            self.desconectar(motivo="Conexão encerrada pelo servidor.")
    
    def pesquisar_nome(self):
        nome = self.campo_nome.text().strip()
        if not nome:
            self.log("⚠️ Informe um nome para pesquisar.")
            return

        request_id = str(uuid.uuid4())
        mensagem = {"tipo": "nome", "valor": nome, "request_id": request_id}
        self.consultas_pendentes[request_id] = {"descricao": f"Consulta por Nome: {nome}", "inicio": time.time()}
        self.enviar_pacote(mensagem)
        self.log(f"🔎 Consulta enviada: Nome = '{nome}'")

    def pesquisar_cpf(self):
        cpf = self.campo_cpf.text().strip()
        if not cpf:
            self.log("⚠️ Informe um CPF para pesquisar.")
            return

        request_id = str(uuid.uuid4())
        mensagem = {"tipo": "cpf", "valor": cpf, "request_id": request_id}
        self.consultas_pendentes[request_id] = {"descricao": f"Consulta por CPF: {cpf}", "inicio": time.time()}
        self.enviar_pacote(mensagem)
        self.log(f"🔎 Consulta enviada: CPF = '{cpf}'")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ClienteWindow()
    window.show()
    sys.exit(app.exec_())