import os
from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QKeySequence, QAction, QGuiApplication
from PyQt6.QtCore import QUrl, Qt
import ruidaqan


class VentanaAyuda(QMainWindow):
    """Ventana para mostrar ayuda dentro del programa."""


    def __init__(self, parent=None, referencia=None):
        super().__init__(parent)

        # Ruta del archivo de ayuda
        two_up = os.path.normpath(__file__).rsplit(os.sep, maxsplit=2)[0]
        path = os.path.join(two_up, 'docs', 'html', 'manual', 'pantallas.html')
        URL = QUrl.fromLocalFile(path)
        # Para abrir la página en una determinada referencia
        if referencia: URL.setFragment(referencia)
        self.setWindowTitle('Ayuda')

        self.VisorTexto = QWebEngineView()
        self.VisorTexto.setUrl(URL)

        self.setCentralWidget(self.VisorTexto)
        self.resize(500, 800)
        self.center()

        self.exit = QAction("Exit", triggered=lambda: self.close())
        self.exit.setShortcuts([QKeySequence("Return"), QKeySequence("Esc")])
        self.addAction(self.exit)

    def center(self):
        """ Center window on screen """
        qr = self.frameGeometry()
        cp = QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


class AboutWindow(QMainWindow):
    """Ventana para información del programa """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle('Acerca de RuiDAQAn')
        # Texto a mostrar en la ventana
        str_vent_about = """<center><b>RuiDAQAn<br>
        <center>versión: %s</b><br>
        commit: %s<br><br>
        Consultas, sugerencias y reportes de errores comunicarse con:<br>
        Pablo A. Bellino<br>
        <a href="mailto:pbellino@cnea.gov.ar">
        pbellino@cnea.gov.ar</a><br><br>
        División Física Experimental de Reactores<br>
        Centro Atómico Constituyentes<br>
        CNEA</center>"""

        # Información sobre versión y hash
        version = ruidaqan.__version__
        commit = ruidaqan.__commit__
        # __commit__ sólo si se corre una distribución
        if commit == "": commit = "en desarrollo"
        self.label = QLabel(str_vent_about%(version, commit))
        self.label.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        # Layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.widget = QWidget(self)
        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

        self.exit = QAction("Exit", triggered=lambda: self.close())
        self.exit.setShortcuts([QKeySequence("Return"), QKeySequence("Esc")])
        self.addAction(self.exit)

