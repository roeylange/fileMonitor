import difflib
import os
import shutil
import time
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from shutil import copyfile

# Configuration
CONFIG_DIRECTORY = os.path.expanduser("~/.monitorProject")
CONFIG_FILE = os.path.join(CONFIG_DIRECTORY, "list.txt")
BACKUP_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "backup")  # Directory to store backups
PASSWORD = "12345"
MAX_ATTEMPTS = 3
DEFAULT_THRESH = 10000
FILE_THRESHOLDS = {
    '.bin': 500,
    '.exe': 500,
    '.dll': 500,
    '.txt': 10000,
    '.log': 10000,
    '.doc': 1000,
    '.docx': 1000,
    '.pdf': 1000,
    '.jpg': 2000,
    '.png': 2000,
    '.gif': 2000,
    '.py': 1500,
    '.sh': 1500,
    '.js': 1500,
}

EXCLUDE_EXTENSIONS = ['.swp', '.swo', '.tmp']

class DeletionHandler(FileSystemEventHandler):
    def on_deleted(self, event):
        if event.is_directory:
            print(f"Detected deletion of folder: {event.src_path}")
            backup_folder_path = os.path.join(BACKUP_DIRECTORY, os.path.basename(event.src_path))
            self.restore_folder(event.src_path, backup_folder_path)
        elif not event.is_directory:
            print(f"Detected deletion of file: {event.src_path}")
            ext = os.path.splitext(event.src_path)[1].lower()
            if ext in EXCLUDE_EXTENSIONS:
                print(f"Excluded deletion of file: {event.src_path}")
                return
            backup_file_path = os.path.join(BACKUP_DIRECTORY, os.path.basename(event.src_path))
            success = self.prompt_password()
            if not success:
                self.restore_file(event.src_path, backup_file_path)
                self.show_restoration_message()

    def on_modified(self, event):
        if not event.is_directory:
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
                if ext in ['.txt', '.log', '.doc', '.docx', '.pdf', '.py', '.sh', '.js']:  # Text or document files
                    with open(backup_file_path, 'r', errors='ignore') as original_file:
                        original_content = original_file.read()
                    with open(file_path, 'r', errors='ignore') as current_file:
                        current_content = current_file.read()
                    difference = sum(1 for _ in difflib.ndiff(original_content, current_content) if _[0] != ' ')
                    if difference >= threshold:
                        print(f"Detected significant character change in {file_path}")
                        success = self.prompt_password()
                        if not success:
                            self.restore_file(file_path, backup_file_path)
                            self.show_restoration_message()
                else:  # Binary files
                    original_size = os.path.getsize(backup_file_path)
                    current_size = os.path.getsize(file_path)
                    if abs(current_size - original_size) >= threshold:
                        print(f"Detected significant size change in {file_path}")
                        success = self.prompt_password()
                        if not success:
                            self.restore_file(file_path, backup_file_path)
                            self.show_restoration_message()

    def prompt_password(self):
        root = tk.Tk()
        root.withdraw()  # Hide the main window

        attempts = 0
        while attempts < MAX_ATTEMPTS:
            password = simpledialog.askstring("Password Required", "Enter password:", show='*')
            if password is None:
                return False  # User cancelled
            if password == PASSWORD:
                return True
            attempts += 1
        return False

    def restore_file(self, file_path, backup_file_path):

        if not os.path.exists(file_path) and os.path.exists(backup_file_path) and os.path.exists(os.path.dirname(file_path)):
            copyfile(backup_file_path, file_path)
            print(f"Restored file: {file_path}")

    def restore_folder(self, folder_path, backup_folder_path):
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)  # Remove the original folder if it exists
        shutil.copytree(backup_folder_path, folder_path)  # Copy the backup folder to the original location
        print(f"Restored folder: {folder_path}")

    def show_restoration_message(self):
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        messagebox.showinfo("Restoration", "File restored due to incorrect password.")

def select_paths():
    """Prompt user to select directories or files to monitor."""
    paths = load_paths()  # Load existing paths
    print(f"Loaded paths: {paths}")  # Debugging information

    def add_file():
        path = filedialog.askopenfilename()
        if path:
            paths.append(path)
            update_paths_list()
        print(f"Added path: {path}")  # Debugging information

    def add_folder():
        path = filedialog.askdirectory()
        if path:
            paths.append(path)
            update_paths_list()
        print(f"Added path: {path}")  # Debugging information

    def remove_path():
        selected = paths_listbox.curselection()
        for index in selected[::-1]:
            paths.pop(index)
        update_paths_list()
        print(f"Removed path at index: {selected}")  # Debugging information

    def update_paths_list():
        paths_listbox.delete(0, tk.END)
        for path in paths:
            paths_listbox.insert(tk.END, path)

    def save_and_exit():
        with open(CONFIG_FILE, 'w') as f:
            for path in paths:
                f.write(path + '\n')
        root.destroy()

    root = tk.Tk()
    root.title("Select Paths to Monitor")

    tk.Button(root, text="Add File", command=add_file).pack()
    tk.Button(root, text="Remove Selected", command=remove_path).pack()
    tk.Button(root, text="Add Folder", command=add_folder).pack()
    

    paths_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE)
    paths_listbox.pack()

    update_paths_list()  # Display the loaded paths

    tk.Button(root, text="Save and Exit", command=save_and_exit).pack()

    root.mainloop()

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

def start_monitoring(paths):
    event_handler = DeletionHandler()
    observer = Observer()
    for path in paths:
        if os.path.exists(path):
            observer.schedule(event_handler, path=path, recursive=True if os.path.isdir(path) else False)
    observer.start()
    print(f"Started monitoring {paths}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def main():
    if not os.path.exists(CONFIG_DIRECTORY):
        os.makedirs(CONFIG_DIRECTORY)

    select_paths()  # Always open the UI to select paths

    paths = load_paths()

    if not os.path.exists(BACKUP_DIRECTORY):
        os.makedirs(BACKUP_DIRECTORY)

    create_initial_backups(paths)
    start_monitoring(paths)

if __name__ == "__main__":
    main()
