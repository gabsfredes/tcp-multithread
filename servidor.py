import sys
import threading
from PyQt5 import QtWidgets
from servidor_gui import Ui_Servidor  # Interface gráfica
from servidor_back import iniciar_servidor, ENCERRAR  # Lógica do servidor

class ServidorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Servidor()
        self.ui.setupUi(self)

        # Conecta os botões da interface às funções
        self.ui.botao_iniciar.clicked.connect(self.iniciar_servidor)
        self.ui.botao_escolher_banco.clicked.connect(self.selecionar_banco)
        self.ui.botao_desligar.clicked.connect(self.desligar_servidor)

        # Variável para controlar o estado do servidor
        self.servidor_thread = None
        self.servidor_ativo = False

    def log_mensagem(self, mensagem):
        """Adiciona uma mensagem ao terminal_informacoes no terminal_servidor."""
        self.ui.terminal_informacoes.append(mensagem)  # Adiciona a mensagem ao QTextEdit
        self.ui.terminal_informacoes.ensureCursorVisible()  # Garante que o scroll acompanhe as mensagens

    def alterar_estado_configuracoes(self, estado):
        """Ativa ou desativa todos os widgets dentro da área de configurações."""
        for widget in self.ui.area_configuracoes.findChildren(QtWidgets.QWidget):
            widget.setEnabled(estado)

    def iniciar_servidor(self):
        if not self.servidor_ativo:
            # Obtém IP, porta e máximo de clientes da interface
            host = self.ui.campo_ip.text() or "127.0.0.1"
            try:
                port = int(self.ui.campo_porta.text())
            except ValueError:
                self.log_mensagem("⚠️ Porta inválida. Insira um número.")
                return

            max_clientes = self.ui.spinbox_maxclientes.value()  # Obtém o valor do spinbox
            self.log_mensagem(f"Máximo de clientes configurado para: {max_clientes}")

            # Atualiza o status e inicia o servidor em uma thread
            self.log_mensagem(f"🚀 Iniciando servidor em {host}:{port}...")
            self.servidor_thread = threading.Thread(target=self.executar_servidor, args=(host, port, max_clientes), daemon=True)
            self.servidor_thread.start()
            self.servidor_ativo = True

            # Desativa a área de configurações e o botão iniciar
            self.ui.area_configuracoes.setEnabled(False)
            self.ui.botao_iniciar.setEnabled(False)
            self.alterar_estado_configuracoes(False)
            self.log_mensagem("✅ Servidor iniciado com sucesso!")
        else:
            self.log_mensagem("⚠️ O servidor já está em execução.")

    def executar_servidor(self, host, port, max_clientes):
        """Executa o servidor e redireciona as mensagens para o terminal."""
        def log_callback(mensagem):
            self.log_mensagem(mensagem)

        # Substitui as mensagens do servidor para usar o log_callback
        iniciar_servidor(host, port, log_callback, max_clientes)

    def desligar_servidor(self):
        """Desliga o servidor."""
        global ENCERRAR
        if self.servidor_ativo:
            self.log_mensagem("⛔ Encerrando servidor...")
            ENCERRAR = True  # Sinaliza para o servidor encerrar
            self.servidor_ativo = False

            # Reativa a área de configurações e o botão iniciar
            self.ui.area_configuracoes.setEnabled(True)
            self.ui.botao_iniciar.setEnabled(True)
            self.alterar_estado_configuracoes(True)
            self.log_mensagem("🛑 Servidor desligado com sucesso.")
        else:
            self.log_mensagem("⚠️ O servidor não está em execução.")

    def selecionar_banco(self):
        # Abre um diálogo para selecionar o arquivo do banco de dados
        caminho, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Selecionar Banco de Dados", "", "Arquivos SQLite (*.db)")
        if caminho:
            self.log_mensagem(f"📂 Banco selecionado: {caminho}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ServidorWindow()
    window.show()
    sys.exit(app.exec_())