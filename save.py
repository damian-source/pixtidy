import os
import shutil
from PyQt5.QtWidgets import QDialog, QMessageBox
from save_dialog import SaveDialog


def save_images(df, save_dir):
    groups = df['Grupa'].unique()
    dialog = SaveDialog(groups)

    if dialog.exec_() == QDialog.Accepted:
        action = dialog.get_action()
        selected_groups = dialog.get_selected_groups()

        for group in selected_groups:
            group_dir = os.path.join(save_dir, group)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)

            group_df = df[df['Grupa'] == group]
            for idx, row in group_df.iterrows():
                src_path = row['Pełna ścieżka pliku']
                base_filename = os.path.basename(src_path)
                dest_path = os.path.join(group_dir, base_filename)

                # Sprawdź, czy plik już istnieje, jeśli tak, dodaj sekwencyjny numer do nazwy
                if os.path.exists(dest_path):
                    filename, ext = os.path.splitext(base_filename)
                    counter = 1
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(group_dir, f"{filename}({counter}){ext}")
                        counter += 1

                if not os.path.exists(src_path):
                    #print(f"Source file does not exist: {src_path}")
                    continue

                try:
                    if action == "copy":
                        shutil.copy(src_path, dest_path)
                    elif action == "move":
                        shutil.move(src_path, dest_path)
                except Exception as e:
                    #print(f"Error processing file {src_path}: {e}")
                    QMessageBox.critical(None, "Error", f"An error occurred while processing file {src_path}: {e}")
                    return False  # Błąd zapisu
        return True  # Zapis zakończony sukcesem
    return False  # Anulowanie operacji

