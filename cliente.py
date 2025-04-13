import sys
import threading
import json
from PyQt5 import QtWidgets
from cliente_gui import Ui_Cliente  # Interface gráfica
import socket

class ClienteWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Cliente()
        self.ui.setupUi(self)

        # Conecta os botões da interface às funções
        self.ui.botao_iniciar.clicked.connect(self.conectar_servidor)
        self.ui.botao_nome.clicked.connect(self.pesquisar_por_nome)
        self.ui.botao_cpf.clicked.connect(self.pesquisar_por_cpf)
        self.ui.botao_desconectar.clicked.connect(self.desconectar_servidor)

        # Variáveis para controlar o estado do cliente
        self.cliente = None
        self.conectado = False

    def log_mensagem(self, mensagem):
        """Adiciona uma mensagem ao terminal_cliente."""
        self.ui.terminal_client_area.append(mensagem)  # Adiciona a mensagem ao QTextEdit
        self.ui.terminal_client_area.ensureCursorVisible()  # Garante que o scroll acompanhe as mensagens

    def conectar_servidor(self):
        """Conecta ao servidor com o IP e porta fornecidos."""
        if not self.conectado:
            ip = self.ui.campo_ip.text() or "127.0.0.1"
            try:
                porta = int(self.ui.campo_porta.text())
            except ValueError:
                self.log_mensagem("⚠️ Porta inválida. Insira um número.")
                return

            try:
                self.cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.cliente.connect((ip, porta))
                self.conectado = True
                self.log_mensagem(f"✅ Conectado ao servidor {ip}:{porta}")

                # Inicia uma thread para ouvir respostas do servidor
                threading.Thread(target=self.ouvir_respostas, daemon=True).start()

                # Desativa os campos de conexão
                self.ui.campo_ip.setEnabled(False)
                self.ui.campo_porta.setEnabled(False)
                self.ui.botao_iniciar.setEnabled(False)
                self.ui.botao_desconectar.setEnabled(True)
            except Exception as e:
                self.log_mensagem(f"❌ Falha na conexão: {e}")
        else:
            self.log_mensagem("⚠️ Já conectado a um servidor.")

    def ouvir_respostas(self):
        """Thread para ouvir respostas do servidor."""
        try:
            while self.conectado:
                dados = self.cliente.recv(8192)
                if not dados:
                    self.log_mensagem("❌ Conexão encerrada pelo servidor.")
                    self.conectado = False
                    break

                try:
                    resposta = json.loads(dados.decode('utf-8'))
                    if resposta["status"] == "ok":
                        self.log_mensagem(f"\n📥 Um resultado foi recebido ({resposta['tempo_execucao_segundos']}s):")
                        for linha in resposta["resultados"]:
                            self.log_mensagem(str(dict(zip(resposta["colunas"], linha))))
                    else:
                        self.log_mensagem(f"⚠️ Erro: {resposta['mensagem']}")
                except json.JSONDecodeError:
                    self.log_mensagem("⚠️ Resposta do servidor em formato inválido.")
        except Exception as e:
            self.log_mensagem(f"❌ Erro crítico na thread de respostas: {e}")
    
    def enviar_comando(self, comando):
        """Envia um comando SQL ao servidor."""
        if self.conectado:
            payload = json.dumps({"sql": comando})
            try:
                self.cliente.sendall(payload.encode('utf-8'))
                if "nome LIKE" in comando:
                    nome = self.ui.campo_nome.text().strip()
                    self.log_mensagem(f"📤 Enviado pesquisa pelo nome:{nome}.")
                elif "cpf =" in comando:
                    cpf = self.ui.campo_cpf.text().strip()
                    self.log_mensagem(f"📤 Enviado pesquisa pelo CPF: {cpf}.")
                else:
                    self.log_mensagem("📤 Comando enviado.")
            except BrokenPipeError:
                self.log_mensagem("❌ Conexão com o servidor foi perdida.")
                self.conectado = False
            except Exception as e:
                self.log_mensagem(f"❌ Falha ao enviar comando: {e}")
                self.conectado = False
        else:
           self.log_mensagem("⚠️ Não conectado a um servidor.")

    def pesquisar_por_nome(self):
        """Pesquisa por nome no servidor."""
        nome = self.ui.campo_nome.text().strip()
        if nome:
            comando = f"SELECT * FROM cpf WHERE nome LIKE '%{nome}%'"
            self.enviar_comando(comando)
        else:
            self.log_mensagem("⚠️ Campo de nome está vazio.")

    def pesquisar_por_cpf(self):
        """Pesquisa por CPF no servidor."""
        cpf = self.ui.campo_cpf.text().strip()
        if cpf:
            comando = f"SELECT * FROM cpf WHERE cpf = '{cpf}'"
            self.enviar_comando(comando)
        else:
            self.log_mensagem("⚠️ Campo de CPF está vazio.")

    def desconectar_servidor(self):
        """Desconecta do servidor."""
        if self.conectado:
            self.log_mensagem("⛔ Desconectando do servidor...")
            try:
                self.cliente.close()
            except Exception as e:
                self.log_mensagem(f"⚠️ Erro ao desconectar: {e}")
            finally:
                self.conectado = False
                self.ui.campo_ip.setEnabled(True)
                self.ui.campo_porta.setEnabled(True)
                self.ui.botao_iniciar.setEnabled(True)
                self.ui.botao_desconectar.setEnabled(False)
                self.log_mensagem("🛑 Desconectado do servidor.")
        else:
            self.log_mensagem("⚠️ Não há conexão ativa para desconectar.")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ClienteWindow()
    window.show()
    sys.exit(app.exec_())