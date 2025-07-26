# -----------------------------------------------------------------------------
# Project: PixTidy
# File: main.py
# Author: Damian Urbański
# Last Updated: November 30, 2024
# -----------------------------------------------------------------------------
# Change Log:
# 
# [November 3, 2024]
# - Updated the cache directory handling to ensure compatibility with different 
#   operating systems. The cache directory now defaults to:
#     - `%LOCALAPPDATA%\PixTidy\cache` on Windows
#     - `~/.cache/pixtidy` on Linux
# - Added logic to create the cache directory if it does not exist and clear 
#   its contents upon reinitialization.
#
# [November 30, 2024] - Changes in table.py
# - Fixed issue with `self.custom_groups` retaining outdated group names.
# - Restored functionality to track and update previous group names during edits.
# - Enhanced group management to ensure consistent synchronization between 
#   table view and the underlying `self.custom_groups` list.
# -----------------------------------------------------------------------------



import sys
import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QProgressBar, QSizePolicy, QFileDialog, QMessageBox
from timeline import TimelineWidget
from maps import MapWidget
from files import ImageThumbnailViewer
from table import TableWidget
import pandas as pd
from save import save_images
import shutil
import os
from PyQt5.QtWidgets import QMenuBar, QAction
from PyQt5.QtGui import QIcon
import platform

# sprawdzenie systemu operacyjnego
if sys.platform.startswith('linux'):
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
elif sys.platform.startswith('win'):
    os.environ['QT_QPA_PLATFORM'] = 'windows'

# Zmiana ustawień wyświetlania data frame
pd.set_option('display.max_rows', None)  # Wyświetla wszystkie wiersze
pd.set_option('display.max_columns', None)  # Wyświetla wszystkie kolumny
pd.set_option('display.width', None)  # Ustawia szerokość wyświetlania do szerokości konsoli
pd.set_option('display.max_colwidth', None)  # Wyświetla całą zawartość każdej kolumny

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PixTidy")
        self.setGeometry(100, 100, 1200, 800)
        
        def get_icon_path():
            if hasattr(sys, '_MEIPASS'):
                return os.path.join(sys._MEIPASS, 'icon.ico')
            else:
                return 'icon.ico'
        
        # Dodaj ikonkę
        self.setWindowIcon(QIcon(get_icon_path()))



        # Dodaj pasek menu
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        # Dodaj menu Help
        help_menu = self.menu_bar.addMenu("Help")

        # Dodaj opcję About w menu Help
        # Opcja About
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        # Opcja Getting Started Video
        video_tutorial_action = QAction("Getting Started Video", self)
        video_tutorial_action.triggered.connect(self.open_video_tutorial)
        help_menu.addAction(video_tutorial_action)

        # Główny widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout dla central_widget
        main_layout = QHBoxLayout()
        self.central_widget.setLayout(main_layout)

        # Layout dla lewej kolumny
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, 1)

        # Layout dla prawej kolumny
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, 1)

        # Dodanie widgetów do lewej kolumny
        self.image_viewer = ImageThumbnailViewer(self)
        self.table_widget = TableWidget(self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(self.image_viewer, 1)
        left_layout.addWidget(self.table_widget, 1)

        # Dodanie widgetów do prawej kolumny
        self.timeline_widget = TimelineWidget(self)
        self.map_widget = MapWidget(self.timeline_widget)

        # Ustawienia dla map_widget
        self.map_widget.setMinimumSize(300, 200)
        self.map_widget.setMaximumSize(600, 800)
        self.map_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Ustawienia dla timeline_widget
        self.timeline_widget.setMinimumSize(300, 200)
        self.timeline_widget.setMaximumSize(600, 200)
        self.timeline_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right_layout.addWidget(self.map_widget, 1)
        right_layout.addWidget(self.timeline_widget, 1)

        # Inicjalizacja zmiennych
        self.current_group = "no category"

        # Połączenie sygnałów
        self.image_viewer.files_loaded.connect(self.new_files_loaded)
        self.image_viewer.loading_progress.connect(self.update_progress)
        self.table_widget.active_group_changed.connect(self.change_activ_group)
        self.table_widget.group_updated.connect(self.update_group)
        self.map_widget.rectangle_selected.connect(self.filter_by_area)
        self.timeline_widget.date_range_changed.connect(self.filter_by_date_range)
        self.table_widget.save_button.clicked.disconnect()
        self.table_widget.save_button.clicked.connect(self.save_all)
        self.table_widget.group_name_changed.connect(self.update_group_in_df)

    def show_about_dialog(self):
        """Wyświetla okno dialogowe z informacjami o aplikacji."""
        QMessageBox.about(self, "About PixTidy",
                          "PixTidy\n"
                          "Version 1.0.3.0\n"
                          "Created by: Damian Urbański\n"
                          "Email: urbanski.automatyka@gmail.com")
        
    def open_video_tutorial(self):
        """ Otwiera okno w domyślenj przeglądarce z filmem Youtube"""
        import webbrowser
        video_url = "https://www.youtube.com/watch?v=v8xnxqdqMMI"
        webbrowser.open(video_url)


    def new_files_loaded(self, df):
        self.current_group = "no category"
        self.refresh_display(df)
        self.table_widget.update_table(self.df, self.current_group)
        # Dodajemy wywołanie show_markers, aby wyświetlić markery dla aktywnej grupy
        self.map_widget.show_markers(self.df[(self.df['Grupa'] == self.current_group)
                                             & (self.df['date_mark'] == True)])

    def change_activ_group(self, group):
        #print(f'change_activ_group funcion - now group is: {group}')
        """ Funkcja przyjmuje za argument grupę, przy której zostało
        kliknięte show w table widget i ustawia aktualną aktywnę grupę
        w klasie MainWindow"""
        self.current_group = group
        self.refresh_display(self.df)
        self.update_group(group) ##############################
        # Dodajemy wywołanie show_markers, aby wyświetlić markery dla aktywnej grupy
        self.map_widget.show_markers(self.df[(self.df['Grupa'] == self.current_group)
                                             & (self.df['date_mark'] == True)])

    def update_group_in_df(self, old_group, new_group):
        """ Funkcja aktualizuje nazwę grupy w self.df oraz odświeża widok """
        #print(f"Updating group name in df from {old_group} to {new_group}")

        # Zaktualizuj wiersze w self.df, gdzie nazwa grupy to old_group
        self.df.loc[self.df['Grupa'] == old_group, 'Grupa'] = new_group

        # Jeżeli zmieniła się nazwa aktywnej grupy to zmień aktywną grupę.
        if old_group == self.current_group:
            self.current_group = new_group

        # Wywołujemy show_markers, aby zaktualizować markery po dodaniu zdjęcia do grupy
        self.map_widget.show_markers(self.df[(self.df['Grupa'] == self.current_group) &
                                             (self.df['date_mark'] == True)], scale_view=False)

    def refresh_display(self, df):
        #print('refresh_display function')
        self.df = df
        # Wywołanie set_photos z self.df i aktualną grupą
        self.timeline_widget.set_photos(self.df, self.current_group)

        # Zaktualizuj widok tabeli
        # self.table_widget.update_table(self.df, self.current_group)  # Zaktualizuj widok tabeli
        self.table_widget.set_df(self.df)  # Ustawienie ramki danych w TableWidget

        # wyświetlenie miniaturek
        # Filtruj DataFrame według grupy i wartości w kolumnach 'map_mark' oraz 'date_mark'
        self.filtered_df = self.df[
            (self.df['Grupa'] == self.current_group) &  # Filtruj po grupie
            (self.df['map_mark'] == True) &  # Filtruj po map_mark == True
            (self.df['date_mark'] == True)  # Filtruj po date_mark == True
            ]
        self.image_viewer.display_images(self.filtered_df)


    def filter_by_date_range(self, selected_dates):
        """
        Funkcja aktualizuje kolumnę 'date_mark' w self.df na podstawie przekazanej listy dat,
        tylko dla aktywnej grupy.
        """
        #print('filter_by_date_range function')

        # Filtruj DataFrame na podstawie aktywnej grupy, używając .loc aby uniknąć kopii
        mask = self.df['Grupa'] == self.current_group
        group_df = self.df.loc[mask]

        # Zapisz obecną kolumnę 'date_mark', niezależnie od tego, czy selected_dates jest pusty
        old_date_mark = group_df['date_mark'].copy()

        if selected_dates:
            # Przekształcenie kolumny 'Data zrobienia zdjęcia' na format daty, jeśli jeszcze nie jest w tym formacie
            self.df.loc[mask, 'parsed_date'] = pd.to_datetime(group_df['Data zrobienia zdjęcia'], format='%Y:%m:%d',
                                                              errors='coerce').dt.date

            # Ustawienie 'date_mark' na True, jeśli data znajduje się na liście 'selected_dates', inaczej False
            self.df.loc[mask, 'date_mark'] = self.df.loc[mask, 'parsed_date'].apply(
                lambda x: True if x in selected_dates else False)

        else:
            # Jeśli lista jest pusta, ustaw wszystkie daty na False (odznacz wszystko)
            self.df.loc[mask, 'date_mark'] = False

        # Sprawdzenie, czy coś się zmieniło w 'date_mark'
        if not self.df.loc[mask, 'date_mark'].equals(old_date_mark):
            # Wywołanie refresh_display tylko, jeśli zaszły zmiany
            self.refresh_display(self.df)
            # Dodajemy wywołanie show_markers, aby zaktualizować markery po filtrowaniu po dacie
            self.map_widget.show_markers(self.df[(self.df['Grupa'] == self.current_group) &
                                                 (self.df['date_mark'] == True)], scale_view=False)



    def filter_by_area(self, lat1, lon1, lat2, lon2):
        #print(f'filter_by_area function - coordinates: {(lat1, lon1, lat2, lon2)}')

        # Tworzymy maskę dla aktywnej grupy
        mask = self.df['Grupa'] == self.current_group

        # Sprawdzenie, czy współrzędne są zerowe, co oznacza usunięcie zaznaczenia obszaru
        if lat1 == 0.0 and lon1 == 0.0 and lat2 == 0.0 and lon2 == 0.0:
            # Zapisz obecną kolumnę 'map_mark'
            old_map_mark = self.df.loc[mask, 'map_mark'].copy()

            # Ustaw wartość 'map_mark' na True dla wszystkich wierszy w masce
            self.df.loc[mask, 'map_mark'] = True

            # Sprawdzenie, czy coś się zmieniło w 'map_mark'
            if not self.df.loc[mask, 'map_mark'].equals(old_map_mark):
                # Wywołanie refresh_display tylko, jeśli zaszły zmiany
                self.refresh_display(self.df)
            return  # Zakończ funkcję, jeśli współrzędne są zerowe

        # Funkcja sprawdzająca, czy wiersz jest w granicach
        def is_within_bounds(row):
            try:
                lat, lon = map(float, row['Koordynaty'].split(', '))
                return lat1 <= lat <= lat2 and lon1 <= lon <= lon2
            except ValueError:
                return False  # Jeśli współrzędne są nieznane lub niepoprawne, zwróć False

        # Zapisz oryginalną kolumnę 'map_mark'
        old_map_mark = self.df.loc[mask, 'map_mark'].copy()

        # Aktualizuj 'map_mark' bezpośrednio w self.df dla wierszy spełniających maskę
        self.df.loc[mask, 'map_mark'] = self.df.loc[mask].apply(lambda row: is_within_bounds(row), axis=1)

        # Sprawdzenie, czy coś się zmieniło w 'map_mark'
        if not self.df.loc[mask, 'map_mark'].equals(old_map_mark):
            # Wywołanie refresh_display tylko, jeśli zaszły zmiany
            self.refresh_display(self.df)


    def update_group(self, group):
        #print('update_group function')

        # Filtruj wiersze, które należą do aktywnej grupy i mają 'date_mark' oraz 'map_mark' ustawione na True
        mask = (self.df['Grupa'] == self.current_group) & (self.df['date_mark'] == True) & (self.df['map_mark'] == True)

        # Zmieniamy grupę na przekazaną w argumencie dla przefiltrowanych wierszy
        self.df.loc[mask, 'Grupa'] = group

        # Ustawienie wartości True dla kolumn 'map_mark' i 'date_mark' w całym DataFrame
        self.df['map_mark'] = True
        self.df['date_mark'] = True

        # wyczyszczenie zaznaczonego na mapie obszaru
        self.map_widget.clear_selection()

        # Wywołanie refresh_display, aby zaktualizować widok
        self.refresh_display(self.df)

        self.table_widget.update_table(self.df, self.current_group)  # Zaktualizuj widok tabeli

        # Dodajemy wywołanie show_markers, aby wyświetlić markery dla aktywnej grupy
        self.map_widget.show_markers(self.df[(self.df['Grupa'] == self.current_group)
                                             & (self.df['date_mark'] == True)])

    def update_progress(self, progress):
        """Funkcja wyświetla pasek postępu ładowania zdjęć"""
        #print(f'update_progress funcion. Progres: {progress}')
        self.progress_bar.setVisible(progress < 100)
        self.progress_bar.setValue(progress)

    def save_all(self):
        #print('save_all funcion funcion')
        if not hasattr(self, 'df') or self.df is None:
            QMessageBox.critical(self, "Error", "No data available to save!")
            return

        options = QFileDialog.Options()
        save_dir = QFileDialog.getExistingDirectory(self, "Select Directory", options=options)
        if save_dir:
            try:
                success = save_images(self.df, save_dir)
                if success:
                    QMessageBox.information(self, "Success", "Files saved successfully!")
                    self.clear_state()  # Resetowanie stanu aplikacji po zapisaniu plików
                else:
                    #print('Zapis anulowany, nie czyścimy stanu aplikacji')
                    pass
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def clear_state(self):
        #print('clear_state funcion')
        # Czyszczenie DataFrame i filtrowanego DataFrame
        self.df = None
        self.filtered_df = None
        self.current_group = None

        # Czyszczenie widżetów
        self.image_viewer.clear()
        self.table_widget.clear()
        self.map_widget.clear_selection()
        self.timeline_widget.clear()
        self.map_widget.marker_manager.clear_markers()  # Czyszczenie pinezek na mapie

        # Czyszczenie paska postępu
        self.progress_bar.reset()
        self.progress_bar.setVisible(False)

        if platform.system() == "Windows":
            cache_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'PixTidy', 'cache')
        elif platform.system() == "Linux":
            cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'pixtidy')
        else:
            raise Exception("Unsupported operating system")

        if os.path.exists(cache_dir):
            #print('czyszczenie katalogu')
            shutil.rmtree(cache_dir)

        # Sprawdzenie czy wszystko zostało wyczyszczoe
        #print(self.df)
        #print(self.filtered_df)
        #print(self.current_group)

if __name__ == "__main__":
    app = QApplication(['', '--no-sandbox'])
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
