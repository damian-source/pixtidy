import sys
import os
import pandas as pd
import cv2
from datetime import datetime

import platform
import subprocess
import json

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QScrollArea, QGridLayout, QDialog, QLabel, QMessageBox, QApplication
from PyQt5.QtWidgets import QHBoxLayout, QSlider  # Do przycisków w odtwarzaczu video
from PyQt5.QtCore import QCoreApplication # blokowanie zamrażania app podczas ładowania plików "program nie odpowiada"
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QUrl # Do odtwarzania video
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent # Do odtwarzania video
from PyQt5.QtMultimediaWidgets import QVideoWidget # Do odtwarzania video
from PIL import Image
from PIL.ExifTags import TAGS
import hashlib


class ImageThumbnailViewer(QWidget):
    files_loaded = pyqtSignal(pd.DataFrame)
    loading_progress = pyqtSignal(int)
    group_updated = pyqtSignal(pd.DataFrame)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        self.openButton = QPushButton('Open Directory', self)
        self.openButton.clicked.connect(self.openDirectory)
        self.layout.addWidget(self.openButton)

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollWidget = QWidget(self)
        self.scrollLayout = QGridLayout(self.scrollWidget)
        self.scrollWidget.setLayout(self.scrollLayout)
        self.scrollArea.setWidget(self.scrollWidget)
        self.layout.addWidget(self.scrollArea)

        self.setLayout(self.layout)


    def openDirectory(self):
        file_dialog = QFileDialog(self, "Select Directory")
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.setOption(QFileDialog.DontUseNativeDialog, True)  # Wymusza niestandardowy dialog PyQt

        if file_dialog.exec_() == QFileDialog.Accepted:
            directory = file_dialog.selectedFiles()[0]  # Pobierz wybrany katalog
            self.loadImages(directory)  # Rozpocznij ładowanie plików



    def get_cache_path(self, filepath):
        import platform
        import os

        # Wybór ścieżki w zależności od systemu operacyjnego
        if platform.system() == "Windows":
            base_cache_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'PixTidy', 'cache')
        elif platform.system() == "Linux":
            base_cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'pixtidy')
        else:
            raise Exception("Unsupported operating system")

        # Tworzenie katalogu cache, jeśli nie istnieje
        if not os.path.exists(base_cache_dir):
            os.makedirs(base_cache_dir)

        # Tworzenie unikalnej nazwy pliku na podstawie ścieżki
        import hashlib
        hash_object = hashlib.md5(filepath.encode())
        filename = hash_object.hexdigest() + '.png'

        return os.path.join(base_cache_dir, filename)


    def loadImages(self, directory):
        image_data = []
        total_files = sum([len(files) for r, d, files in os.walk(directory)])
        current_file = 0
        failed_files = []  # Lista do przechowywania ścieżek plików, które nie zostały wczytane

        for root, dirs, files in os.walk(directory):
            for filename in files:
                #print(f'loadImage, filename: {filename}')
                filepath = os.path.join(root, filename)
                cache_path = self.get_cache_path(filepath)

                # Obsługa obrazów
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    #print('loadImages - photo')
                    if not os.path.exists(cache_path):
                        try:
                            with Image.open(filepath) as img:
                                img.thumbnail((100, 100))
                                img.save(cache_path)
                        except Exception as e:
                            failed_files.append(f"{filepath}: Error creating thumbnail - {e}")
                            continue  # Przechodzimy do następnego pliku

                    try:
                        metadata = self.get_image_metadata(filepath)
                        # Sprawdzamy, czy są wymagane metadane (koordynaty, data i rozdzielczość)
                        if self.is_valid_metadata(metadata):
                            image_data.append(metadata)
                        else:
                            failed_files.append(
                                f"{filepath}: Invalid metadata (Coordinates, Date, or Resolution missing or invalid)")
                    except Exception as e:
                        failed_files.append(f"{filepath}: Error loading image metadata - {e}")
                        continue  # Przechodzimy do następnego pliku

                # Obsługa wideo
                elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    #print('loadImages - video')
                    if not os.path.exists(cache_path):
                        try:
                            self.create_video_thumbnail(filepath, cache_path)
                        except Exception as e:
                            failed_files.append(f"{filepath}: Error creating video thumbnail - {e}")
                            continue  # Przechodzimy do następnego pliku
                    try:
                        metadata = self.get_video_metadata(filepath)
                        # Sprawdzamy, czy są wymagane metadane (koordynaty, data i rozdzielczość)
                        if self.is_valid_metadata(metadata):
                            image_data.append(metadata)
                        else:
                            failed_files.append(
                                f"{filepath}: Invalid metadata (Coordinates, Date, or Resolution missing or invalid)")
                    except Exception as e:
                        failed_files.append(f"{filepath}: Error loading video metadata - {e}")
                        continue  # Przechodzimy do następnego pliku

                current_file += 1
                progress = int((current_file / total_files) * 100)
                self.loading_progress.emit(progress)

                # Przetwarzanie zdarzeń co 100 plików, aby UI nie "zamrażało"
                # Zapobiega wyskakiwaniu okienka "program nie odpowiada"
                if current_file % 10 == 0:
                    QCoreApplication.processEvents()

        # Tworzenie DataFrame z metadanych obrazów i wideo
        df = pd.DataFrame(image_data)

        if df.empty:
            self.show_empty_df_message()  # Wywołaj okno dialogowe, jeśli df jest pusty

        if not df.empty:
            df.index += 1  # Numerowanie od 1
            df.insert(0, 'Liczba porządkowa', df.index)

            # Dodanie kolumny Grupa i ustawienie wartości domyślnych
            df['Grupa'] = 'no category'

            # Dodanie kolumn map_mark i date_mark, domyślnie ustawionych na True
            df['map_mark'] = True
            df['date_mark'] = True

            # Emitowanie sygnału po zakończeniu ładowania plików
            self.loading_progress.emit(100)
            self.files_loaded.emit(df)

        # Jeśli są pliki, które się nie załadowały, wyświetl okno dialogowe
        if failed_files:
            self.show_failed_files_dialog(failed_files)

    def is_valid_metadata(self, metadata):
        """
        Sprawdza, czy metadane są ważne.
        Pliki z koordynatami 'Unknown' lub (0,0) są traktowane jako błędne.
        """
        # Sprawdzenie koordynatów
        coords = metadata['Koordynaty']
        if coords == 'Unknown':
            return False

        try:
            lat, lon = map(float, coords.split(', '))
            if lat == 0.0 and lon == 0.0:  # Sprawdzenie, czy współrzędne nie są (0,0)
                return False
        except ValueError:
            return False  # Jeśli nie można przekonwertować na float, uznajemy metadane za błędne

        # Sprawdzenie innych metadanych
        if metadata['Data zrobienia zdjęcia'] == 'Unknown' or metadata['Rozdzielczość pliku'] == 'Unknown':
            return False

        return True

    def show_empty_df_message(self):
        """Wyświetla okno dialogowe, gdy DataFrame jest pusty."""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("No Images Loaded")
        msg_box.setText("No valid images found to load.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def show_failed_files_dialog(self, failed_files):
        """Wyświetla okno dialogowe z listą plików, które nie zostały załadowane."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Failed to Load Files")
        dialog.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout(dialog)

        # Tworzymy etykietę z informacją o błędach
        label = QLabel(
            "The following files could not be loaded due to missing or invalid metadata (Coordinates, Date, or Resolution):")
        layout.addWidget(label)

        # Dodajemy scroll area dla listy plików
        scroll_area = QScrollArea(dialog)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Dodajemy pliki do layoutu
        for file_info in failed_files:
            failed_file_label = QLabel(file_info)
            scroll_layout.addWidget(failed_file_label)

        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Dodajemy przycisk OK
        ok_button = QPushButton("OK", dialog)
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)

        dialog.exec_()

    def get_image_metadata(self, filepath):
        try:
            with Image.open(filepath) as img:
                exif_data = img._getexif() or {}
                exif = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}

                resolution = f"{img.width}x{img.height}"
                coordinates = self.get_coordinates(exif)
                date_time = exif.get('DateTime', 'Unknown').split()
                date = date_time[0] if date_time else 'Unknown'
                time = date_time[1] if len(date_time) > 1 else 'Unknown'

                return {
                    'Pełna ścieżka pliku': filepath,
                    'Rozdzielczość pliku': resolution,
                    'Koordynaty': coordinates,
                    'Data zrobienia zdjęcia': date,
                    'Godzina zrobienia zdjęcia': time
                }
        except Exception as e:
            #print(f"Error processing image {filepath}: {e}")
            return {
                'Pełna ścieżka pliku': filepath,
                'Rozdzielczość pliku': 'Unknown',
                'Koordynaty': 'Unknown',
                'Data zrobienia zdjęcia': 'Unknown',
                'Godzina zrobienia zdjęcia': 'Unknown'
            }

    def get_coordinates(self, exif):
        gps_info = exif.get('GPSInfo')
        if not gps_info:
            return 'Unknown'

        def get_decimal_from_dms(dms, ref):
            degrees, minutes, seconds = dms
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            if ref in ['S', 'W']:
                decimal = -decimal
            return decimal

        try:
            lat = get_decimal_from_dms(gps_info[2], gps_info[1])
            lon = get_decimal_from_dms(gps_info[4], gps_info[3])
            return f"{lat}, {lon}"
        except (IndexError, KeyError, ValueError):
            return 'Unknown'



    # Nowa wersja funkcji get_video_metadata
    def get_ffprobe_path(self):
        system = platform.system()
        if system == "Linux":
            return os.path.join("ffmpeg-binaries", "linux", "ffprobe")
        elif system == "Darwin":  # macOS
            return os.path.join("ffmpeg-binaries", "macos", "ffprobe")
        elif system == "Windows":
            return os.path.join("ffmpeg-binaries", "windows", "ffprobe.exe")
        else:
            raise Exception(f"Unsupported system: {system}")

    def get_video_metadata(self, filepath):
        ffprobe = self.get_ffprobe_path()
        command = [
            ffprobe, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filepath
        ]

        # Ukryj konsolę na Windows
        if platform.system() == "Windows":
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        metadata = json.loads(result.stdout)

        # Reszta funkcji
        video_stream = next((stream for stream in metadata['streams'] if stream['codec_type'] == 'video'), None)
        resolution = f"{video_stream['width']}x{video_stream['height']}" if video_stream else "Unknown"

        tags = metadata.get('format', {}).get('tags', {})
        gps_latitude = tags.get('location-eng', 'Unknown').split('+')[1] if 'location-eng' in tags else 'Unknown'
        gps_longitude = tags.get('location-eng', 'Unknown').split('+')[2].rstrip('/') if 'location-eng' in tags else 'Unknown'

        creation_time = tags.get('creation_time', 'Unknown')
        if creation_time != 'Unknown':
            date_taken = creation_time.split('T')[0].replace('-', ':')
            time_taken = creation_time.split('T')[1].split('.')[0]
        else:
            date_taken = 'Unknown'
            time_taken = 'Unknown'

        wynik = {
            'Pełna ścieżka pliku': filepath,
            'Rozdzielczość pliku': resolution,
            'Koordynaty': f"{gps_latitude}, {gps_longitude}",
            'Data zrobienia zdjęcia': date_taken,
            'Godzina zrobienia zdjęcia': time_taken
        }

        return wynik

    def create_video_thumbnail(self, video_path, thumbnail_path):
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                #print(f"Successfully read a frame from {video_path}")
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame)
                pil_img.thumbnail((100, 100))
                pil_img.save(thumbnail_path)
                #print(f"Thumbnail saved to {thumbnail_path}")
        cap.release()

    def display_images(self, df):
        #print("Displaying images...")
        #print(df)
        self.clearLayout(self.scrollLayout)
        row, col = 0, 0
        for index, row_data in df.iterrows():
            filepath = row_data['Pełna ścieżka pliku']
            cache_path = self.get_cache_path(filepath)
            #print(f"Attempting to load thumbnail from {cache_path}")
            try:
                pixmap = QPixmap(cache_path)
                #print(f"Pixmap null status: {pixmap.isNull()}")
                if not pixmap.isNull():
                    #print(f"Successfully loaded thumbnail from {cache_path}")
                    thumbnail = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    label = ClickableLabel(filepath, self)
                    label.setPixmap(thumbnail)
                    label.clicked.connect(self.showImage)
                    self.scrollLayout.addWidget(label, row, col)
                    #print(f"Added thumbnail to layout at row {row}, col {col}")
                    col += 1
                    if col > 4:  # 5 miniaturek w jednym rzędzie
                        col = 0
                        row += 1
                else:
                    #print(f"Unable to load image: {filepath}")
                    pass
            except Exception as e:
                #print(f"Error loading image {filepath}: {e}")
                pass

    def showImage(self, filepath):
        if filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            dialog = ImageDialog(filepath, self)
        elif filepath.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            dialog = VideoDialog(filepath, self)
        else:
            return  # Jeśli plik nie jest zdjęciem ani wideo, nie rób nic.
        dialog.exec_()

    def clearLayout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def update_group(self, group):
        self.df.loc[self.df.index.isin(self.filtered_df.index), 'Grupa'] = group
        self.group_updated.emit(self.df)

    def clear(self):
        self.clearLayout(self.scrollLayout)


class ClickableLabel(QLabel):
    clicked = pyqtSignal(str)

    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath

    def mousePressEvent(self, event):
        self.play_video()

    def play_video(self):
        system = platform.system()
        if system == "Windows":
            # Otwórz wideo w domyślnym odtwarzaczu na Windows
            os.startfile(self.filepath)
        elif system == "Darwin":  # macOS
            # Otwórz wideo w domyślnym odtwarzaczu na macOS
            subprocess.run(["open", self.filepath])
        elif system == "Linux":
            # Otwórz wideo w domyślnym odtwarzaczu na Linux
            subprocess.run(["xdg-open", self.filepath])
        else:
            raise Exception(f"Unsupported system: {system}")


class ImageDialog(QDialog):
    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Image Viewer')
        self.setGeometry(100, 100, 600, 600)
        layout = QVBoxLayout(self)
        pixmap = QPixmap(filepath)
        label = QLabel(self)
        label.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(label)
        self.setLayout(layout)


def get_ffplay_path():
    system = platform.system()
    if system == "Linux":
        return os.path.join("ffmpeg-binaries", "linux", "ffplay")
    elif system == "Darwin":  # macOS
        return os.path.join("ffmpeg-binaries", "macos", "ffplay")
    elif system == "Windows":
        return os.path.join("ffmpeg-binaries", "windows", "ffplay.exe")
    else:
        raise Exception(f"Unsupported system: {system}")





if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = ImageThumbnailViewer()
    viewer.show()
    sys.exit(app.exec_())