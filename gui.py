import os
import sys

if getattr(sys, "frozen", False):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(sys._MEIPASS, "ms-playwright")

import asyncio
from pathlib import Path
from typing import List, Tuple, Dict, Union
import requests
from bs4 import BeautifulSoup
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QTextEdit, QLineEdit, QPushButton, QFileDialog, QProgressBar, QSizePolicy
from PySide6.QtGui import QPalette, QColor, QCursor, QIcon
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QMimeData
from downloader import main as download_main

# Common stylesheet applied to text and button widgets throughout the app
COMMON_CSS = '''
    QTextEdit, QLineEdit {
        border: 1px solid #353535;
        border-radius: 4px;
        selection-background-color: rgb(76, 194, 255);
        selection-color: #ffffff;
    }
    QTextEdit:focus, QLineEdit:focus {
        border: 1px solid rgb(76, 194, 255);
    }
    QPushButton {
        background-color: rgb(35,35,35);
        border: 1px solid #3A3A3A;
        border-radius: 4px;
        color: white;
        padding: 6px 14px;
    }
    QPushButton:enabled:hover {
        background-color: rgb(80,80,80);
        border: 1px solid #555555;
    }
    QPushButton:enabled:pressed {
        background-color: rgb(100,100,100);
        border: 1px solid #777777;
    }
    QPushButton:disabled {
        background-color: rgb(40,40,40);
        border: 1px solid #2A2A2A;
        color: rgb(160,160,160);
    }
'''

def icon_path(icon_path: str) -> str:
    if getattr(sys, 'frozen', False):
        base_path: str = sys._MEIPASS
    else:
        base_path: str = os.path.abspath('.')
    return os.path.join(base_path, icon_path)

class PasteEdit(QTextEdit):
    def insertFromMimeData(self, source: QMimeData) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        super().insertFromMimeData(source)
        cursor.insertText('\n')
        cursor.endEditBlock()

def fetch_runway_metadata(url: str) -> Tuple[str, str, str, str]:
    response = requests.get(url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')

    raw_title = soup.select_one('.pageTitle').get_text(strip = True)
    designer, _, album, gender = raw_title.split(' - ')
    
    season = soup.select_one('.season').get_text(strip = True)

    return designer, gender, season, album

class PreviewWorker(QThread):
    preview_result = Signal(str, object)

    def __init__(self, urls: List[str], cache: Dict[str, Tuple[str, str, str, str]]) -> None:
        super().__init__()
        self.urls = urls
        self.cache = cache
        self._isRunning = True

    def run(self) -> None:
        for url in self.urls:
            if not self._isRunning:
                break
            if 'https://www.firstview.com/collection_images.php?id=' not in url:
                self.preview_result.emit(url, 'invalid')
                continue
            if url in self.cache:
                result = self.cache[url]
            else:
                try:
                    result = fetch_runway_metadata(url)
                    self.cache[url] = result
                except Exception:
                    self.preview_result.emit(url, 'invalid')
                    continue
            self.preview_result.emit(url, result)

    def stop(self) -> None:
        self._isRunning = False

class DownloadWorker(QThread):
    status = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, urls: List[str], path: Path) -> None:
        super().__init__()
        self.urls = urls
        self.path = path

    def run(self) -> None:
        try:
            asyncio.run(download_main(self.urls, self.path, lambda message: self.status.emit(message)))
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('FirstView Downloader')
        self.resize(900, 600)
        self.setMinimumSize(900, 600)
        self.setDarkTheme()

        self.preview_cache: Dict[str, Tuple[str, str, str, str]] = {}
        self._has_invalid = False
        self._current_label: Union[str, None] = None

        self._setup_ui()
        self.download_button.setEnabled(False)

        # Preview timer
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(100)
        self.preview_timer.timeout.connect(self.update_preview)
        self.paste_text.textChanged.connect(self.preview_timer.start)

    def _setup_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet(COMMON_CSS)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        main_layout.addLayout(self._make_top_panel())
        main_layout.addWidget(self._make_progress_container())
        main_layout.addLayout(self._make_bottom_panel())

        self.setCentralWidget(central)

    def _make_top_panel(self) -> QHBoxLayout:
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # URL input
        paste_layout = QVBoxLayout()
        paste_label = QLabel('Paste First View URLs: (one per line)')
        paste_label.setAlignment(Qt.AlignLeft)
        self.paste_text = PasteEdit()
        paste_layout.addWidget(paste_label)
        paste_layout.addWidget(self.paste_text)

        # Preview box
        preview_layout = QVBoxLayout()
        preview_label = QLabel('Preview:')
        preview_label.setAlignment(Qt.AlignLeft)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setTextInteractionFlags(Qt.NoTextInteraction)
        self.preview_text.setFocusPolicy(Qt.NoFocus)
        self.preview_text.viewport().setCursor(QCursor(Qt.ArrowCursor))
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self.preview_text)

        top_layout.addLayout(paste_layout)
        top_layout.addLayout(preview_layout)
        return top_layout

    def _make_progress_container(self) -> QWidget:
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_grid = QGridLayout(container)
        self.progress_grid.setContentsMargins(0, 0, 10, 0)
        self.progress_grid.setHorizontalSpacing(10)
        self.progress_grid.setColumnStretch(0, 0)
        self.progress_grid.setColumnStretch(1, 1)
        self.progress_grid.setColumnStretch(2, 0)
        return container

    def _make_bottom_panel(self) -> QHBoxLayout:
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        # Download path changer
        path_layout = QHBoxLayout()
        download_label = QLabel('Download Path:')
        default_path = Path.home() / 'Downloads' / 'FirstView'
        default_path.mkdir(parents = True, exist_ok = True)
        self.path_edit = QLineEdit(str(default_path))
        change_button = QPushButton('Change')
        change_button.setFixedWidth(100)
        change_button.clicked.connect(self.change_download_location)
        path_layout.addWidget(download_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(change_button)
        bottom_layout.addLayout(path_layout)

        # Download button
        self.download_button = QPushButton('Download')
        self.download_button.setFixedWidth(100)
        self.download_button.clicked.connect(self.download)
        bottom_layout.addWidget(self.download_button, alignment = Qt.AlignRight)
        return bottom_layout

    def setDarkTheme(self) -> None:
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(53, 53, 53))
        pal.setColor(QPalette.WindowText, Qt.white)
        pal.setColor(QPalette.Base, QColor(25, 25, 25))
        pal.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        pal.setColor(QPalette.ToolTipBase, Qt.white)
        pal.setColor(QPalette.ToolTipText, Qt.white)
        pal.setColor(QPalette.Text, Qt.white)
        QApplication.setPalette(pal)

    def change_download_location(self) -> None:
        new_directory = QFileDialog.getExistingDirectory(self, 'Select Download Folder')
        if new_directory:
            self.path_edit.setText(new_directory)

    def update_preview(self) -> None:
        urls = [url.strip() for url in self.paste_text.toPlainText().splitlines() if url.strip()]
        self.preview_text.clear()
        self._has_invalid = False
        self.download_button.setEnabled(False)

        if not urls:
            return
        
        if hasattr(self, 'preview_worker') and self.preview_worker.isRunning():
            self.preview_worker.stop()
            
        self.preview_worker = PreviewWorker(urls, self.preview_cache)
        self.preview_worker.preview_result.connect(self.on_preview_result)
        self.preview_worker.finished.connect(self.on_preview_loaded)
        self.preview_worker.start()

    def on_preview_loaded(self) -> None:
        if not self._has_invalid:
            self.download_button.setEnabled(True)

    def on_preview_result(self, url: str, res: Union[Tuple[str, str, str, str], str]) -> None:
        if res == 'invalid' or isinstance(res, Exception):
            self.preview_text.append(f'Invalid URL: {url}')
            self._has_invalid = True
        else:
            designer, gender, season, album = res
            self.preview_text.append(f'{designer} - {gender} - {season} - {album}')

    def download(self) -> None:
        urls = [url.strip() for url in self.paste_text.toPlainText().splitlines() if url.strip()]
        if not urls or self._has_invalid:
            return

        download_path = Path(self.path_edit.text())
        download_path.mkdir(parents = True, exist_ok = True)

        # Clear existing progress widgets
        for i in reversed(range(self.progress_grid.count())):
            widget = self.progress_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self._current_label = None
        self.progress_label = None
        self.progress_bar = None
        self.progress_count = None

        self.download_button.setEnabled(False)
        self.download_worker = DownloadWorker(urls, download_path)
        self.download_worker.status.connect(self.on_status)
        self.download_worker.error.connect(lambda e: self.preview_text.append(f'Error: {e}'))
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()

    def on_status(self, message: str) -> None:
        if not message.startswith('PROGRESS:'):
            self.preview_text.append(message)
            return

        _, label, currently_downloaded, total_images = message.split(':')
        current = int(currently_downloaded)
        total = int(total_images)

        if label != getattr(self, '_current_label', None):
            self._current_label = label
            if self.progress_label is None:
                self.progress_label = QLabel(label)
                self.progress_bar = QProgressBar()
                self.progress_bar.setTextVisible(False)
                self.progress_count = QLabel(f'0/{total}')
                self.progress_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

                self.progress_grid.addWidget(self.progress_label, 0, 0, alignment = Qt.AlignLeft)
                self.progress_grid.addWidget(self.progress_bar, 0, 1)
                self.progress_grid.addWidget(self.progress_count, 0, 2)
            else:
                self.progress_label.setText(label)

            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(0)
            self.progress_count.setText(f'0/{total}')

        self.progress_bar.setValue(current)
        self.progress_count.setText(f'{current}/{total}')

    def on_download_finished(self) -> None:
        self.download_button.setEnabled(True)

    def showEvent(self, event) -> None:
        super().showEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    icon_file : str = icon_path('fv.ico')
    app.setWindowIcon(QIcon(icon_path('fv.ico')))
    window = MainWindow()
    window.setWindowIcon(QIcon(icon_file))
    window.setWindowIconText('FirstView Downloader')
    window.show()
    sys.exit(app.exec())
