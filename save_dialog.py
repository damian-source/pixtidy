from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QCheckBox, QPushButton, QLabel, \
    QButtonGroup, QListWidget, QListWidgetItem, QMessageBox
from PyQt5.QtCore import Qt


class SaveDialog(QDialog):
    def __init__(self, groups, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Photos")
        self.setGeometry(100, 100, 400, 300)

        self.layout = QVBoxLayout(self)

        self.label = QLabel("Choose action:")
        self.layout.addWidget(self.label)

        self.button_group = QButtonGroup(self)
        self.copy_radio = QRadioButton("Copy")
        self.move_radio = QRadioButton("Move")
        self.copy_radio.setChecked(True)
        self.button_group.addButton(self.copy_radio)
        self.button_group.addButton(self.move_radio)

        self.layout.addWidget(self.copy_radio)
        self.layout.addWidget(self.move_radio)

        self.group_label = QLabel("Select groups:")
        self.layout.addWidget(self.group_label)

        self.list_widget = QListWidget(self)
        for group in groups:
            item = QListWidgetItem(group)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list_widget.addItem(item)

        self.layout.addWidget(self.list_widget)

        self.button_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.deselect_all_button = QPushButton("Deselect All")
        self.button_layout.addWidget(self.select_all_button)
        self.button_layout.addWidget(self.deselect_all_button)

        self.layout.addLayout(self.button_layout)

        self.select_all_button.clicked.connect(self.select_all)
        self.deselect_all_button.clicked.connect(self.deselect_all)

        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.layout.addWidget(self.save_button)
        self.layout.addWidget(self.cancel_button)

    def select_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked)

    def deselect_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)

    def get_selected_groups(self):
        selected_groups = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected_groups.append(item.text())
        return selected_groups

    def get_action(self):
        if self.copy_radio.isChecked():
            return "copy"
        else:
            return "move"

    def accept(self):
        # Sprawdzamy, czy wybrano jakieś grupy
        selected_groups = self.get_selected_groups()
        if not selected_groups:
            # Jeśli nie, wyświetlamy komunikat o błędzie i nie zamykamy okna
            QMessageBox.warning(self, "No Selection", "No groups selected for saving.")
            return
        # Jeśli są zaznaczone grupy, zamykamy okno i kontynuujemy zapis
        super().accept()
