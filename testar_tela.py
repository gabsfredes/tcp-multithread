import sys
from PyQt5 import QtWidgets
from cliente_tela import Ui_Cliente  


class ClienteWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Cliente()
        self.ui.setupUi(self)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ClienteWindow()
    window.show()
    sys.exit(app.exec_())