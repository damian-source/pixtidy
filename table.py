from PyQt5.QtWidgets import QWidget, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QHeaderView
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from save import save_images


class TableWidget(QWidget):
    active_group_changed = pyqtSignal(str)
    group_updated = pyqtSignal(str)
    group_name_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.df = None  # Dodanie atrybutu df
        self.previous_group_name = None  # do sprawdzania, czy nazwa grupy się zmieniła
        self.custom_groups = []  # Zainicjuj custom_groups tutaj

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # Dodanie tabeli
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Count", "Group", "Add to Group", "Show"])
        self.layout.addWidget(self.table)

        # Ustawienie szerokości kolumn
        self.table.setColumnWidth(0, 50)  # Szerokość kolumny "Count" pozostaje sztywna
        self.table.setColumnWidth(2, 100)  # Szerokość kolumny "Add to Group" pozostaje sztywna
        self.table.setColumnWidth(3, 100)  # Szerokość kolumny "Show" pozostaje sztywna

        # Kolumna "Group" dostosowuje się do rozmiaru okna
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        # Kolumny "Count", "Add to Group", i "Show" pozostają sztywne
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)

        # Dodanie przycisków
        self.button_layout = QHBoxLayout()

        self.add_row_button = QPushButton('Add Row', self)
        self.add_row_button.clicked.connect(self.add_row)
        self.button_layout.addWidget(self.add_row_button)

        self.save_button = QPushButton('Save All', self)
        self.save_button.clicked.connect(self.save_all)
        self.button_layout.addWidget(self.save_button)

        self.layout.addLayout(self.button_layout)

        self.setLayout(self.layout)
        self.group_counter = 1

        # Wywołanie funkcji, gdy któraś komórka w tabeli zostanie kliknięta
        self.table.cellClicked.connect(self.on_group_name_click)

        # Wywołanie funkcji, gdy zmieni się wartość w komórce w tabeli
        self.table.cellChanged.connect(self.on_group_name_changed)

    def on_group_name_click(self, row, col):
        """ Funkcja zapisuje nazwę grupy gdy któraś komórka w tabeli zostanie kliknięta"""
#       #print('on_group_name_click funcion')
        if col == 1:  # Sprawdzamy, czy kliknięcie jest w kolumnie grupy
            self.previous_group_name = self.table.item(row, col).text()
        

    def on_group_name_changed(self, row, col):
        """ Funkcja sprawdza, czy użytkownik zmienił nazwę istniejącej grupy """
        #print(f'on_group_name_changed called for row={row}, col={col}')
        #print(f" col: {col}, self.previous_group_name: {self.previous_group_name}")
        if col == 1 and self.previous_group_name is not None:
            new_group_name = self.table.item(row, col).text()

            # Sprawdzenie, czy nowa nazwa grupy już istnieje
            if new_group_name in self.custom_groups and new_group_name != self.previous_group_name:
                # Wyświetlenie komunikatu o błędzie
                QMessageBox.warning(self, "Error",
                                    f"Group name '{new_group_name}' already exists. Please choose another name.")

                # Przywrócenie starej nazwy grupy
                self.table.item(row, col).setText(self.previous_group_name)
                self.previous_group_name = None  # Resetujemy nazwę, aby uniknąć zapętlenia
                return

            # Sprawdzenie, czy zmiana dotyczy grupy w custom_groups
            #print(f'self.custom_groups in on_group_name_changed funcion {self.custom_groups}')
            #print(f'self.previous_group_name in on_group_name_changed funcion {self.previous_group_name}')
            if self.previous_group_name in self.custom_groups:
                # Aktualizacja nazwy grupy w custom_groups
                self.custom_groups[self.custom_groups.index(self.previous_group_name)] = new_group_name
                #print(f'Updated custom_groups: {self.custom_groups}')

            # Wyemituj sygnał, aby zaktualizować nazwę grupy w self.df (wywołanie funkcji w main.py)
            self.group_name_changed.emit(self.previous_group_name, new_group_name)

            # Zresetuj previous_group_name po zmianie
            self.previous_group_name = None


        

    def set_df(self, df):
        self.df = df

    def save_all(self):
        if self.df is None:
            QMessageBox.critical(self, "Error", "No data available to save!")
            return

        options = QFileDialog.Options()
        save_dir = QFileDialog.getExistingDirectory(self, "Select Directory", options=options)
        if save_dir:
            try:
                save_images(self.df, save_dir)
                QMessageBox.information(self, "Success", "Files saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def update_table(self, df, current_group):
        #('update_table function')

        # Tymczasowo blokuj sygnały, aby uniknąć niepotrzebnych wywołań
        self.table.blockSignals(True)

        # Wyczyszczenie tabeli
        self.table.setRowCount(0)

        # Grupy i liczba plików w każdej grupie z df
        groups = df['Grupa'].unique()

        # Zaktualizuj listę, uwzględniając tylko nowe grupy
        new_groups = [group for group in groups if group not in self.custom_groups]
        self.custom_groups.extend(new_groups)
        #print(f'self.custom_groups in update_table funcion {self.custom_groups}')
        # Wyświetl wszystkie grupy, w tym puste
        for group in self.custom_groups:
            count = len(df[df['Grupa'] == group])

            # Dodanie wiersza do tabeli
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            # Kolumna Count
            count_item = QTableWidgetItem(str(count))
            self.table.setItem(row_position, 0, count_item)

            # Kolumna Group
            group_item = QTableWidgetItem(group)
            self.table.setItem(row_position, 1, group_item)

            # Kolumna Add to Group z przyciskiem OK
            add_button = QPushButton('OK')
            add_button.clicked.connect(self.on_add_to_group_click)
            self.table.setCellWidget(row_position, 2, add_button)

            # Kolumna Show z przyciskiem Show
            show_button = QPushButton('Show')
            show_button.clicked.connect(self.on_show_click)
            self.table.setCellWidget(row_position, 3, show_button)

            # Jeśli ta grupa jest aktywną grupą, pokoloruj wiersz na zielono
            if group == current_group:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row_position, col)
                    if item:
                        item.setBackground(Qt.green)

        # Odblokuj sygnały po zakończeniu operacji
        self.table.blockSignals(False)


    def add_row(self):
        #print('add_row function')

        # Tymczasowo blokuj sygnały, aby uniknąć wywołania on_group_name_changed
        self.table.blockSignals(True)

        row_position = self.table.rowCount()

        # Tworzymy nazwę nowej grupy
        new_group = f"Group_{self.group_counter}"
        self.group_counter += 1

        # Dodajemy nową grupę do listy custom_groups
        self.custom_groups.append(new_group)
        #print(f'self.custom_groups in add_row funcion {self.custom_groups}')

        # Dodajemy wiersz do tabeli
        self.table.insertRow(row_position)

        # Kolumna Group
        self.table.setItem(row_position, 1, QTableWidgetItem(new_group))

        # Kolumna Add to Group z przyciskiem OK
        add_button = QPushButton('OK')
        add_button.clicked.connect(self.on_add_to_group_click)
        self.table.setCellWidget(row_position, 2, add_button)

        # Kolumna Show z przyciskiem Show
        show_button = QPushButton('Show')
        show_button.clicked.connect(self.on_show_click)
        self.table.setCellWidget(row_position, 3, show_button)

        # Odblokuj sygnały po zakończeniu operacji
        self.table.blockSignals(False)


    def on_show_click(self):
        #print('on_show_funcion')
        button = self.sender()
        if button:
            row = self.table.indexAt(button.pos()).row()
            group_item = self.table.item(row, 1)
            if group_item:
                group = group_item.text()

                # Emitujemy sygnał, że aktywna grupa została zmieniona
                self.active_group_changed.emit(group)

    def on_add_to_group_click(self):
        #print('on_add_to_gruop')
        button = self.sender()
        if button:
            row = self.table.indexAt(button.pos()).row()
            group_item = self.table.item(row, 1)
            if group_item:
                group = group_item.text()
                self.group_updated.emit(group)

    def clear(self):
        #print('clear funcion')
        self.table.setRowCount(0)
        self.custom_groups = []
        self.group_counter = 1
