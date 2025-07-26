from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, \
    QAbstractItemView, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
import pandas as pd
import datetime


class TimelineWidget(QWidget):
    date_range_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Tworzenie tabeli z trzema kolumnami: Date Taken, Number of Photos, Select
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Date Taken', 'Number of Photos', 'Select'])
        self.table.horizontalHeader().setSectionResizeMode(0,
                                                           QHeaderView.ResizeToContents)  # Kolumna daty ma dynamiczną szerokość
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Kolumna ilości zdjęć się rozszerza
        self.table.horizontalHeader().setSectionResizeMode(2,
                                                           QHeaderView.ResizeToContents)  # Kolumna wyboru dostosowuje się do checkboxa
        self.table.setSelectionMode(QAbstractItemView.NoSelection)

        # Ustawienie layoutu dla widgetu
        layout = QVBoxLayout()
        table_layout = QHBoxLayout()  # Nowy layout z przyciskami po prawej stronie
        table_layout.addWidget(self.table)

        # Dodanie przycisków do zaznaczania i odznaczania checkboxów
        button_layout = QVBoxLayout()  # Layout na przyciski
        self.select_all_button = QPushButton("Select All", self)
        self.deselect_all_button = QPushButton("Deselect All", self)

        # Podłączenie akcji do przycisków
        self.select_all_button.clicked.connect(self.select_all_active)
        self.deselect_all_button.clicked.connect(self.deselect_all_active)

        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.deselect_all_button)
        button_layout.addStretch()  # Dodanie rozciągliwego miejsca, aby przyciski były u góry

        table_layout.addLayout(button_layout)  # Dodanie layoutu z przyciskami do głównego layoutu tabeli

        layout.addLayout(table_layout)
        self.setLayout(layout)

        # Listy do przechowywania zdjęć
        self.photos = []
        self.filtered_photos = []
        self.min_date = None
        self.max_date = None

    def set_photos(self, df, current_group):
        """
        Funkcja przyjmuje cały DataFrame i aktywną grupę,
        filtruje według tej grupy i wyświetla checkboxy zgodnie z wartościami w kolumnie 'date_mark'.
        Jeśli wszystkie wiersze dla danej daty mają 'map_mark' na False, wiersz w tabeli robi się szary
        i checkbox jest zablokowany.
        """

        # Filtruj DataFrame na podstawie aktywnej grupy
        group_df = df[df['Grupa'] == current_group]

        # Tworzenie słownika z datami i informacjami o zdjęciach (map_mark i date_mark)
        date_dict = {}
        for index, row in group_df.iterrows():
            # Konwertowanie na datetime z określonym formatem daty
            date = pd.to_datetime(row['Data zrobienia zdjęcia'], format='%Y:%m:%d', errors='coerce')

            # Pominięcie wartości NaT
            if pd.isna(date):
                continue

            date = date.date()  # Pobierz tylko część daty (bez czasu)

            if date not in date_dict:
                date_dict[date] = {'count': 0, 'all_map_mark_false': True, 'date_mark': row['date_mark']}

            # Aktualizacja liczby zdjęć dla danej daty
            date_dict[date]['count'] += 1

            # Jeśli chociaż jedno zdjęcie z tej daty ma map_mark na True, ustaw 'all_map_mark_false' na False
            if row['map_mark']:
                date_dict[date]['all_map_mark_false'] = False

        # Sortowanie dat od najnowszej do najstarszej
        sorted_dates = sorted(date_dict.items(), key=lambda x: x[0], reverse=True)

        # Ustawienie liczby wierszy w tabeli
        self.table.setRowCount(len(sorted_dates))

        selected_dates = []  # Lista do przechowywania zaznaczonych dat

        for row, (date, data) in enumerate(sorted_dates):
            # Ustawianie daty w tabeli
            date_item = QTableWidgetItem(date.strftime("%A, %d %B %Y"))
            date_item.setFlags(date_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, date_item)

            # Ustawianie liczby zdjęć
            count_item = QTableWidgetItem(str(data['count']))
            count_item.setFlags(count_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, count_item)

            # Tworzenie checkboxa i ustawianie jego stanu zgodnie z wartością w 'date_mark'
            check_box = QCheckBox(self)
            check_box.setTristate(False)  # Checkbox ma być dwustanowy
            check_box.setChecked(data['date_mark'])  # Ustaw checkbox na podstawie wartości w 'date_mark'

            if check_box.isChecked():
                selected_dates.append(date)  # Dodaj datę do listy zaznaczonych dat

            # Jeśli wszystkie zdjęcia z tej daty mają map_mark na False, zablokuj checkbox i wyszarz wiersz
            if data['all_map_mark_false']:
                check_box.setEnabled(False)  # Zablokuj checkbox
                date_item.setBackground(Qt.lightGray)  # Wyszarz datę
                count_item.setBackground(Qt.lightGray)  # Wyszarz liczbę zdjęć

            # Podłącz event zmiany stanu checkboxa
            check_box.stateChanged.connect(self.update_filtered_photos)
            self.table.setCellWidget(row, 2, check_box)

        # Przekazanie listy zaznaczonych dat do updateSelectedDates
        self.updateSelectedDates(selected_dates)  # Funkcja updateSelectedDates otrzyma listę zaznaczonych dat

    def select_all_active(self):
        """ Zaznacz wszystkie aktywne checkboxy """
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 2)
            if checkbox and checkbox.isEnabled():  # Tylko aktywne checkboxy
                checkbox.setChecked(True)

    def deselect_all_active(self):
        """ Odznacz wszystkie aktywne checkboxy """
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 2)
            if checkbox and checkbox.isEnabled():  # Tylko aktywne checkboxy
                checkbox.setChecked(False)

    def update_filtered_photos(self):
        """
        Funkcja aktualizująca listę wybranych (zaznaczonych) dat po zmianie stanu checkboxa.
        """
        selected_dates = []

        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 2)
            if checkbox.isChecked():  # Jeśli checkbox jest zaznaczony
                date_str = self.table.item(row, 0).text()
                date = datetime.datetime.strptime(date_str, "%A, %d %B %Y").date()
                selected_dates.append(date)

        # Wywołaj updateSelectedDates z listą zaznaczonych dat
        self.updateSelectedDates(selected_dates)

    def updateSelectedDates(self, selected_dates):
        #print('TimeLineWidget updateSelectedDates fucion')
        # Emitowanie sygnału z listą dat
        self.date_range_changed.emit(selected_dates)

    def reset_event_colors(self):
        """
        Przywraca wszystkie kolory w tabeli do domyślnych i aktywuje wszystkie checkboxy.
        """
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setBackground(Qt.white)
            self.table.item(row, 1).setBackground(Qt.white)
            checkbox = self.table.cellWidget(row, 2)
            if checkbox:
                checkbox.setEnabled(True)
                checkbox.setStyleSheet("")  # Usuwa szary styl i przywraca normalny wygląd

    def clear(self):
        self.table.clearContents()
        self.table.setRowCount(0)
        self.photos = []
        self.filtered_photos = []
        self.min_date = None
        self.max_date = None
