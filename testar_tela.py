import sys
from PyQt5 import QtWidgets
from servidor_tela import Ui_Servidor  


class ServidorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Servidor()
        self.ui.setupUi(self)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ServidorWindow()
    window.show()
    sys.exit(app.exec_())