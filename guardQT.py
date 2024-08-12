import ctypes
import difflib
import json
import os
import shutil
import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from shutil import copyfile

# Configuration
CONFIG_DIRECTORY = os.path.expanduser("~/.monitorProject")
CONFIG_FILE = os.path.join(CONFIG_DIRECTORY, "list.txt")
PASSWORD_FILE = os.path.join(CONFIG_DIRECTORY, "password.txt")
BACKUP_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "backup")  # Directory to store backups
THRESHOLDS_FILE = os.path.join(CONFIG_DIRECTORY, "file_thresholds.json")
MAX_ATTEMPTS = 3
DEFAULT_THRESH = 10000
EXCLUDE_EXTENSIONS = ['.swp', '.swo', '.tmp']
BINARY_EXTENSIONS = ['.bin', '.exe', '.dll']

def load_thresholds():
    if not os.path.exists(THRESHOLDS_FILE):
        return {}
    with open(THRESHOLDS_FILE, 'r') as f:
        return json.load(f)

def save_thresholds(thresholds):
    with open(THRESHOLDS_FILE, 'w') as f:
        json.dump(thresholds, f, indent=4)

FILE_THRESHOLDS = load_thresholds()

class DeletionHandler(FileSystemEventHandler, QtCore.QObject):
    password_requested = QtCore.pyqtSignal()
    password_result = QtCore.pyqtSignal(bool)

    def __init__(self, app, paths, observer):
        super().__init__()
        self.app = app
        self.password_requested.connect(self.on_password_requested)
        self.password_result.connect(self.on_password_result)
        self.password_dialog_result = None
        self.file_to_restore = None
        self.paths = paths
        self.restoring = False
        self.observer = observer

    def on_deleted(self, event):
        if os.path.isfile(event.src_path):
            print(f"Detected deletion of file: {event.src_path}")
            ext = os.path.splitext(event.src_path)[1].lower()
            if ext in EXCLUDE_EXTENSIONS:
                print(f"Excluded deletion of file: {event.src_path}")
                return
            self.file_to_restore = (event.src_path, os.path.join(BACKUP_DIRECTORY, os.path.basename(event.src_path)))
            self.request_password()
        else:
            print(f"Detected deletion of folder: {event.src_path}")
            backup_folder_path = os.path.join(BACKUP_DIRECTORY, os.path.basename(event.src_path))
            self.file_to_restore = (event.src_path, backup_folder_path)
            self.request_password()

    def on_modified(self, event):
        if not os.path.exists(event.src_path):
            self.on_deleted(event)
        elif not event.is_directory:
            print(f"Detected modification of file: {event.src_path}")
            self.check_modification(event.src_path)

    def check_modification(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        threshold = FILE_THRESHOLDS.get(ext, DEFAULT_THRESH)
        print(f"The threshold is: {threshold}")
        print(f"The ext is: {ext}")
        if threshold is not None:
            backup_file_path = os.path.join(BACKUP_DIRECTORY, os.path.basename(file_path))
            if os.path.exists(backup_file_path):
                if ext not in BINARY_EXTENSIONS:  # Text or document files
                    with open(backup_file_path, 'r', errors='ignore') as original_file:
                        original_content = original_file.read()
                    with open(file_path, 'r', errors='ignore') as current_file:
                        current_content = current_file.read()
                    difference = sum(1 for _ in difflib.ndiff(original_content, current_content) if _[0] != ' ')
                    if difference >= threshold:
                        print(f"Detected significant character change in {file_path}")
                        self.file_to_restore = (file_path, backup_file_path)
                        self.request_password()
                else:  # Binary files
                    original_size = os.path.getsize(backup_file_path)
                    current_size = os.path.getsize(file_path)
                    if abs(current_size - original_size) >= 0:
                        print(f"Detected significant size change in {file_path}")
                        self.file_to_restore = (file_path, backup_file_path)
                        self.request_password()

    def request_password(self):
        self.password_dialog_result = None  # Reset the result
        QtCore.QMetaObject.invokeMethod(self, "on_password_requested", QtCore.Qt.QueuedConnection)
        while self.password_dialog_result is None:
            self.app.processEvents()

    @QtCore.pyqtSlot()
    def on_password_requested(self):
        password, ok = QtWidgets.QInputDialog.getText(None, "Password Required", "Enter password:", QtWidgets.QLineEdit.Password)

        with open(PASSWORD_FILE, 'r') as f:
            saved_password = f.read().strip()

        attempts = 0
        while attempts < MAX_ATTEMPTS:
            if not ok:
                self.password_dialog_result = False
                self.password_result.emit(False)
                return  # User cancelled
            if password == saved_password:
                self.password_dialog_result = True
                self.password_result.emit(True)
                return
            attempts += 1
            password, ok = QtWidgets.QInputDialog.getText(None, "Password Required", "Enter password:", QtWidgets.QLineEdit.Password)
        self.password_dialog_result = False
        self.password_result.emit(False)

    def on_password_result(self, result):
        if not result and self.file_to_restore:
            self.restoring = True
            src_path, backup_path = self.file_to_restore
            if os.path.isfile(backup_path):
                self.restore_file(src_path, backup_path)
                self.show_restoration_message()
            else:
                self.restore_folder(src_path, backup_path)
        self.file_to_restore = None
        if not self.restoring:
            create_initial_backups(self.paths)
        self.restoring = False
        # self.restart_observer()

    def restore_file(self, file_path, backup_file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if os.path.exists(backup_file_path):
            copyfile(backup_file_path, file_path)
            print(f"Restored file: {file_path}")
            QtCore.QTimer.singleShot(0, self.restart_observer)

    def restore_folder(self, folder_path, backup_folder_path):
        os.makedirs(folder_path, exist_ok=True)
        for root, dirs, files in os.walk(backup_folder_path):
            for file in files:
                rel_dir = os.path.relpath(root, backup_folder_path)
                src_file_path = os.path.join(folder_path, rel_dir, file)
                backup_file_path = os.path.join(root, file)
                self.restore_file(src_file_path, backup_file_path)
        print(f"Restored folder: {folder_path}")
        QtCore.QTimer.singleShot(0, self.restart_observer)

    def show_restoration_message(self):
        QtCore.QMetaObject.invokeMethod(self, "show_message", QtCore.Qt.QueuedConnection)

    @QtCore.pyqtSlot()
    def show_message(self):
        QtWidgets.QMessageBox.information(None, "Restoration", "File restored due to incorrect password.")

    def restart_observer(self):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5)
            if self.observer.is_alive():
                print("Observer did not stop in time, forcefully terminating...")
                stop_thread(self.observer)
        self.observer = Observer()
        for path in self.paths:
            if os.path.exists(path):
                self.observer.schedule(self, path=path, recursive=True if os.path.isdir(path) else False)
        self.observer.start()
        print("Observer restarted.")

def stop_thread(thread):
    """Raises an exception in the threads with id thread_id"""
    tid = thread.ident
    if not tid:
        return
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(SystemExit))
    if res == 0:
        raise ValueError("Invalid thread id")
    elif res != 1:
        # if it returns a number greater than one, we're in trouble, and should call it again with exc=NULL to revert the effect
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

def select_paths():
    """Prompt user to select directories or files to monitor."""
    paths = load_paths()  # Load existing paths
    print(f"Loaded paths: {paths}")  # Debugging information

    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("Select Paths to Monitor")
    dialog.setWindowIcon(QtGui.QIcon("icon.png"))

    layout = QtWidgets.QVBoxLayout(dialog)

    label_instructions = QtWidgets.QLabel("Use the buttons below to add or remove files and directories to monitor:")
    layout.addWidget(label_instructions)

    def add_file():
        path, _ = QtWidgets.QFileDialog.getOpenFileName()
        if path:
            paths.append(path)
            update_paths_list()
        print(f"Added path: {path}")  # Debugging information

    def add_folder():
        path = QtWidgets.QFileDialog.getExistingDirectory()
        if path:
            paths.append(path)
            update_paths_list()
        print(f"Added path: {path}")  # Debugging information

    def remove_path():
        selected = paths_listbox.selectedItems()
        for item in selected:
            paths.remove(item.text())
        update_paths_list()
        print(f"Removed path: {selected}")  # Debugging information

    def update_paths_list():
        paths_listbox.clear()
        for path in paths:
            paths_listbox.addItem(path)

    def save_and_exit():
        with open(CONFIG_FILE, 'w') as f:
            for path in paths:
                f.write(path + '\n')
        if not set_or_verify_password(dialog):
            dialog.reject()
            sys.exit("Password verification failed.")
        dialog.accept()

    def modify_thresholds():
        threshold_dialog = ThresholdDialog()
        threshold_dialog.exec_()

    button_add_file = QtWidgets.QPushButton("Add File")
    button_add_file.setStyleSheet("background-color: lightblue;")
    button_add_file.clicked.connect(add_file)
    layout.addWidget(button_add_file)

    button_remove_path = QtWidgets.QPushButton("Remove Selected")
    button_remove_path.setStyleSheet("background-color: lightcoral;")
    button_remove_path.clicked.connect(remove_path)
    layout.addWidget(button_remove_path)

    button_add_folder = QtWidgets.QPushButton("Add Folder")
    button_add_folder.setStyleSheet("background-color: lightgreen;")
    button_add_folder.clicked.connect(add_folder)
    layout.addWidget(button_add_folder)

    button_modify_thresholds = QtWidgets.QPushButton("Modify Thresholds")
    button_modify_thresholds.setStyleSheet("background-color: lightyellow;")
    button_modify_thresholds.clicked.connect(modify_thresholds)
    layout.addWidget(button_modify_thresholds)

    paths_listbox = QtWidgets.QListWidget()
    layout.addWidget(paths_listbox)

    update_paths_list()  # Display the loaded paths

    button_save_and_exit = QtWidgets.QPushButton("Save and Exit")
    button_save_and_exit.setStyleSheet("background-color: lightgrey;")
    button_save_and_exit.clicked.connect(save_and_exit)
    layout.addWidget(button_save_and_exit)

    dialog.exec_()

def set_or_verify_password(parent):
    if not os.path.exists(PASSWORD_FILE):
        password, ok = QtWidgets.QInputDialog.getText(parent, "Set Password", "Create a new password:", QtWidgets.QLineEdit.Password)
        if password:
            with open(PASSWORD_FILE, 'w') as f:
                f.write(password)
            print("Password set successfully.")
            return True
        else:
            QtWidgets.QMessageBox.critical(parent, "Error", "Password cannot be empty.")
            return False
    else:
        with open(PASSWORD_FILE, 'r') as f:
            saved_password = f.read().strip()

        attempts = 0
        while attempts < MAX_ATTEMPTS:
            password, ok = QtWidgets.QInputDialog.getText(parent, "Password Required", "Enter password:", QtWidgets.QLineEdit.Password)
            if not ok:
                return False  # User cancelled
            if password == saved_password:
                return True
            attempts += 1
        QtWidgets.QMessageBox.critical(parent, "Error", "Incorrect password. Exiting.")
        return False

def create_initial_backups(paths):
    """Create initial backups of all files and directories in the paths."""
    for path in paths:
        if os.path.isfile(path):
            backup_file_path = os.path.join(BACKUP_DIRECTORY, os.path.basename(path))
            copyfile(path, backup_file_path)
            print(f"Backup created for file: {path}")
        elif os.path.isdir(path):
            backup_dir_path = os.path.join(BACKUP_DIRECTORY, os.path.basename(path))
            if os.path.exists(backup_dir_path) and backup_dir_path != BACKUP_DIRECTORY:
                shutil.rmtree(backup_dir_path)
                print(f"Deleted existing backup directory: {backup_dir_path}")
            if not os.path.exists(backup_dir_path):
                shutil.copytree(path, backup_dir_path)
                print(f"Backup created for directory: {path}")

def load_paths():
    """Load paths from the config file."""
    if not os.path.exists(CONFIG_FILE):
        return []
    with open(CONFIG_FILE, 'r') as f:
        paths = [line.strip() for line in f.readlines()]
    return paths

def start_monitoring(paths, app):
    observer = Observer()
    event_handler = DeletionHandler(app, paths, observer)
    for path in paths:
        if os.path.exists(path):
            observer.schedule(event_handler, path=path, recursive=True if os.path.isdir(path) else False)
    observer.start()
    print(f"Started monitoring {paths}")

    # Use QTimer to periodically run the event loop
    timer = QtCore.QTimer()

    while True:
        if not event_handler.restoring:
            app.exec_()
    observer.stop()
    observer.join()

class ThresholdDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modify File Thresholds")
        self.setGeometry(200, 200, 400, 300)
        self.layout = QtWidgets.QVBoxLayout(self)

        self.list_widget = QtWidgets.QListWidget()
        self.layout.addWidget(self.list_widget)

        self.load_thresholds()

        self.add_button = QtWidgets.QPushButton("Add Threshold")
        self.add_button.clicked.connect(self.add_threshold)
        self.layout.addWidget(self.add_button)

        self.remove_button = QtWidgets.QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected)
        self.layout.addWidget(self.remove_button)

        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.clicked.connect(self.save_thresholds)
        self.layout.addWidget(self.save_button)

    def load_thresholds(self):
        self.list_widget.clear()
        for ext, thresh in FILE_THRESHOLDS.items():
            self.list_widget.addItem(f"{ext}: {thresh}")

    def add_threshold(self):
        ext, ok1 = QtWidgets.QInputDialog.getText(self, "Add Extension", "Enter file extension (e.g., .txt):")
        if ok1 and ext:
            thresh, ok2 = QtWidgets.QInputDialog.getInt(self, "Add Threshold", "Enter threshold value:")
            if ok2:
                FILE_THRESHOLDS[ext] = thresh
                self.list_widget.addItem(f"{ext}: {thresh}")

    def remove_selected(self):
        for item in self.list_widget.selectedItems():
            ext = item.text().split(':')[0].strip()
            if ext in FILE_THRESHOLDS:
                del FILE_THRESHOLDS[ext]
            self.list_widget.takeItem(self.list_widget.row(item))

    def save_thresholds(self):
        save_thresholds(FILE_THRESHOLDS)
        self.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)

    if not os.path.exists(CONFIG_DIRECTORY):
        os.makedirs(CONFIG_DIRECTORY)

    if len(sys.argv) > 1 and sys.argv[1] == 'refresh':
        # Refresh the backup
        paths = load_paths()
        create_initial_backups(paths)
        print("Backup refreshed.")
        return

    select_paths()  # Always open the UI to select paths

    paths = load_paths()

    if not os.path.exists(BACKUP_DIRECTORY):
        os.makedirs(BACKUP_DIRECTORY)

    create_initial_backups(paths)
    start_monitoring(paths, app)

if __name__ == "__main__":
    main()
