import os
from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QKeySequence, QAction, QGuiApplication
from PyQt6.QtCore import QUrl, Qt
import ruidaqan
from .pantalla import ajusta_tamano


def ruta_ayuda():
    """
    Archivo HTML de la ayuda.

    - Paquete instalado: la copia incluida en el paquete
      (ruidaqan/docs/html, que arma make dist).
    - Desde el repositorio (versión de desarrollo): docs/_build/html, que es
      lo que genera make docs. Se prefiere a la copia del paquete porque esa
      queda de la última vez que se corrió make dist y puede estar
      desactualizada.
    """
    pagina = os.path.join('manual', 'pantallas.html')
    paquete = os.path.normpath(os.path.join(
                    os.path.dirname(__file__), '..', 'docs', 'html', pagina))
    # src/ruidaqan/gui/ventanas_ayuda.py -> raíz del repositorio
    raiz = os.path.normpath(__file__).rsplit(os.sep, maxsplit=4)[0]
    desarrollo = os.path.join(raiz, 'docs', '_build', 'html', pagina)
    es_repositorio = os.path.isfile(os.path.join(raiz, 'docs', 'conf.py'))
    candidatos = [desarrollo, paquete] if es_repositorio else [paquete]
    for ruta in candidatos:
        if os.path.exists(ruta):
            return ruta
    return candidatos[0]


class VentanaAyuda(QMainWindow):
    """Ventana para mostrar ayuda dentro del programa."""


    def __init__(self, parent=None, referencia=None):
        super().__init__(parent)

        path = ruta_ayuda()

        self.setWindowTitle('Ayuda')
        self.VisorTexto = QWebEngineView()

        if os.path.exists(path):
            URL = QUrl.fromLocalFile(path)
            # Para abrir la página en una determinada referencia
            if referencia: URL.setFragment(referencia)
            self.VisorTexto.setUrl(URL)
        else:
            # Sin la documentación compilada se vería una página en blanco
            self.VisorTexto.setHtml(
                "<h3>No se encontró la ayuda</h3>"
                "<p>La ayuda se genera con Sphinx a partir de la carpeta "
                "<code>docs</code> del repositorio:</p>"
                "<ul><li><code>make docs</code> (para usar desde el "
                "repositorio) o</li>"
                "<li><code>make dist</code> (la incluye en el paquete "
                "instalable).</li></ul>"
                f"<p>Se buscó en:<br><code>{path}</code></p>")

        self.setCentralWidget(self.VisorTexto)
        ajusta_tamano(self, 500, 800)
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
        Reactor RA-3<br>
        Centro Atómico Ezeiza<br>
        CNEA</center>"""

        # Información sobre versión y hash
        version = ruidaqan.__version__
        commit = ruidaqan.__commit__
        # __commit__ sólo si se corre una distribución
        # if commit == "": commit = "en desarrollo"
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

