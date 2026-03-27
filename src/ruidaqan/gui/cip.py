#! /usr/bin/env python3
import sys
import os
import pickle
import numpy as np
from datetime import datetime, time

from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QVBoxLayout, QPushButton, QWidget, QTableView,
                             QFormLayout, QLineEdit, QLabel, QHBoxLayout,
                             QAbstractItemView, QDialog, QDialogButtonBox,
                             QMessageBox)



class TableModel(QtCore.QAbstractTableModel):
    def __init__(self, data=None, header=None):
        super(TableModel, self).__init__()
        self._data = data or []
        self.header = header


    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            # status, text = self.todos[index.row()]
            value = self._data[index.row()][index.column()]
            # Formato para mostrar floats
            if isinstance(value, float):
                return f"{value:.3E}"
            # Formato para mostrar tiempos
            if isinstance(value, type(time())):
                return value.strftime("%H:%M:%S")
        # Para alinear contenido de las celdas
        if role == Qt.ItemDataRole.TextAlignmentRole:
            value = self._data[index.row()][index.column()]
            return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)


    def rowCount(self, index):
        return len(self._data)


    def columnCount(self, index):
        # Porque inicializo una tabla vacia
        if self._data:
            return len(self._data[0])
        else:
            return 0


    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self.header[section])
            elif orientation == Qt.Orientation.Vertical:
                return str(section + 1)



class InputIpValues(QtWidgets.QMainWindow):

    cip_manual_win_closed = pyqtSignal(list)

    def __init__(self):
        super().__init__()

        self.FILE_NAME = "ingresos_manuales_cip.pkl"

        self.init_ui()

        self.header = ["Hora", "Ip [A]", "Incerteza Ip [A]"]

        # Para saber si se grabaron los datos
        self.grabado = False

        self.model = TableModel(header=self.header)
        self.load()
        self.first_time = True if not self.model._data else False
        self.tableView.setModel(self.model)

        # Connect the button.
        self.add_btn.pressed.connect(self.add)
        self.del_btn.pressed.connect(self.delete)
        self.end_btn.pressed.connect(self.end_measurement)


    def init_ui(self):
        self.resize(400, 400)
        self.setWindowTitle("Ingresar valores de Ip")
        self.center()
        self.layout = QVBoxLayout()

        # Formulario para ingresar datos de Ip y su incerteza
        self.frm_lab1 = QLabel("Ip [A]:")
        self.frm_edi1 = QLineEdit()
        self.frm_lab2 = QLabel("Incerteza Ip [A]:")
        self.frm_edi2 = QLineEdit()
        self.frm_layout = QFormLayout()
        self.frm_layout.addRow(self.frm_lab1, self.frm_edi1)
        self.frm_layout.addRow(self.frm_lab2, self.frm_edi2)
        # Botones ingresar / borrar datos de la tabla
        self.add_btn = QPushButton("Ingresar")
        self.del_btn = QPushButton("Borrar")
        self.btns_lay = QHBoxLayout()
        self.btns_lay.addWidget(self.add_btn)
        self.btns_lay.addWidget(self.del_btn)
        # Botón para finalizar
        self.end_btn = QPushButton("Finalizar")

        self.tableView = QTableView()
        # Selecciono por filas
        self.tableView.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows)
        self.layout.addWidget(self.tableView)
        self.layout.addLayout(self.frm_layout)
        self.layout.addLayout(self.btns_lay)
        self.layout.addWidget(self.end_btn)

        self.mainbox = QWidget(self)
        self.mainbox.setLayout(self.layout)
        self.setCentralWidget(self.mainbox)


    def center(self):
        """ Center window on screen """
        qr = self.frameGeometry()
        cp = QtGui.QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    def _set_column_width(self):
        for i in range(len(self.header)):
            self.tableView.setColumnWidth(i, 120)
        #self.tableView.resizeColumnsToContents()


    def add(self):
        """
        Add an item to our todo list, getting the text from the QLineEdit .todoEdit
        and then clearing it.
        """
        text_I = self.frm_edi1.text()
        text_std = self.frm_edi2.text()
        text_I = text_I.strip()  # Remove whitespace from the ends
        text_std = text_std.strip()  # Remove whitespace from the ends
        if text_I and text_std: # Don't add empty strings.
            try:
                float_I = float(text_I)
                float_std = float(text_std)
            except:
                print("Los valores ingresados deben ser números")
            else:
                # Time
                now_time = datetime.now().time()
                # Access the list via the model.
                self.model._data.append([now_time, float_I, float_std])
                # Trigger refresh.
                self.model.layoutChanged.emit()
                # Cambio tamaño de columnas en caso de se el primer dato
                if len(self.model._data) == 1:
                    for i in range(len(self.header)):
                        self.tableView.setColumnWidth(i, 120)
                # Empty the input
                self.frm_edi1.setText("")
                self.frm_edi2.setText("")
        if self.first_time: self._set_column_width()
        self.save()


    def delete(self):
        """
        Borra datos seleccionado
        """
        indexes = self.tableView.selectedIndexes()
        if indexes:
            # Selecciono un elemento por cada fila
            ind_to_remove = [indexes[i] for i in range(0, len(indexes),
                                                    len(self.model._data[0]))]

            for ind in sorted(ind_to_remove, reverse=True):
                del self.model._data[ind.row()]
            self.model.layoutChanged.emit()
            self.tableView.clearSelection()
            self.save()
        # Si se borraron todos los datos
        if self.model.columnCount(0)==0: self.empty_table=True


    def end_measurement(self):
        Ip = [(it[1], it[2]) for it in self.model._data]
        # Al menos debe haber un valor de Ip ingresado
        if len(Ip) >= 1:
            # Se emite señal con los datos
            self.cip_manual_win_closed.emit(Ip)
            print(f"Datos grabados: {Ip}")
            self.grabado = True
            self.close()
            try:
                os.remove(self.FILE_NAME)
            except:
                pass
        else:
            print("Se debe introducir al menos un valor")


    def closeEvent(self, event):
        if not self.grabado:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Advertencia")
            dlg.setText("Se debe finalizar la medición antes de salir")
            dlg.setIcon(QMessageBox.Icon.Warning)
            button = dlg.exec()

            if button == QMessageBox.StandardButton.Ok:
                event.ignore()
                # event.accept() # OJO: sólo para debugg, debe ignorare


    def save(self):
        with open(self.FILE_NAME, 'wb') as f:
            pickle.dump(self.model._data, f)


    def load(self):
        try:
            with open(self.FILE_NAME, "rb") as f:
                self.model._data = pickle.load(f)
        except:
            pass



if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    window = InputIpValues()
    window.show()
    app.exec()


