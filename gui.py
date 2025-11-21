import os
import sys

if getattr(sys, "frozen", False):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(sys._MEIPASS, "ms-playwright")

import asyncio
from pathlib import Path
from typing import List, Tuple, Dict, Union
import requests
from bs4 import BeautifulSoup
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton, QFileDialog,
    QProgressBar, QSizePolicy, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QPalette, QColor, QCursor, QIcon, QFont
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QMimeData

from downloader import main as download_main

# Minimalist color scheme
COLORS = {
    'bg': '#121212',
    'card': '#1e1e1e',
    'card_hover': '#252525',
    'border': '#2a2a2a',
    'text': '#e4e4e7',
    'text_secondary': '#a1a1aa',
    'accent': '#3b82f6',
    'accent_hover': '#60a5fa',
    'success': '#22c55e',
    'error': '#ef4444',
    'input_bg': '#161616',
}

STYLESHEET = f'''
QMainWindow {{
    background-color: {COLORS['bg']};
}}

QWidget {{
    font-family: 'Segoe UI', 'Inter', sans-serif;
    color: {COLORS['text']};
}}

QLabel {{
    font-size: 13px;
    color: {COLORS['text_secondary']};
}}

QLabel#title {{
    font-size: 24px;
    font-weight: 600;
    color: {COLORS['text']};
}}

QLabel#subtitle {{
    font-size: 13px;
    color: {COLORS['text_secondary']};
}}

QLabel#sectionLabel {{
    font-size: 12px;
    font-weight: 500;
    color: {COLORS['text_secondary']};
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QTextEdit, QLineEdit {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 12px;
    font-size: 13px;
    color: {COLORS['text']};
    selection-background-color: {COLORS['accent']};
}}

QTextEdit:focus, QLineEdit:focus {{
    border-color: {COLORS['accent']};
}}

QTextEdit#preview {{
    background-color: {COLORS['card']};
    border: none;
    color: {COLORS['text_secondary']};
}}

QPushButton {{
    background-color: {COLORS['accent']};
    border: none;
    border-radius: 8px;
    color: white;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}

QPushButton:pressed {{
    background-color: #2563eb;
}}

QPushButton:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['text_secondary']};
}}

QPushButton#secondary {{
    background-color: transparent;
    border: 1px solid {COLORS['border']};
    color: {COLORS['text']};
}}

QPushButton#secondary:hover {{
    background-color: {COLORS['card_hover']};
    border-color: {COLORS['text_secondary']};
}}

QProgressBar {{
    background-color: {COLORS['border']};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 4px;
}}

QFrame#card {{
    background-color: {COLORS['card']};
    border-radius: 12px;
    border: 1px solid {COLORS['border']};
}}
'''


def icon_path(icon_path: str) -> str:
    if getattr(sys, 'frozen', False):
        base_path: str = sys._MEIPASS
    else:
        base_path: str = os.path.abspath('.')
    return os.path.join(base_path, icon_path)


class PasteEdit(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Segoe UI", 10))
        self.setAcceptRichText(False)
        self.setPlaceholderText("Paste runway URLs here, one per line...")

    def insertFromMimeData(self, source: QMimeData) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.insertText(source.text() + '\n')
        cursor.endEditBlock()


def fetch_runway_metadata(url: str) -> Tuple[str, str, str, str]:
    """Fetch metadata from FirstView URL."""
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    raw_title = soup.select_one('.pageTitle').get_text(strip=True)
    designer, _, album, gender = raw_title.split(' - ')
    season = soup.select_one('.season').get_text(strip=True)
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

            # Check if URL is a valid FirstView URL
            if 'firstview.com/collection_images.php?id=' not in url:
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
            asyncio.run(download_main(self.urls, self.path, lambda msg: self.status.emit(msg)))
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('FirstView Downloader')
        self.resize(600, 700)
        self.setMinimumSize(500, 600)

        self.preview_cache: Dict[str, Tuple[str, str, str, str]] = {}
        self._has_invalid = False
        self._current_label: Union[str, None] = None

        self._setup_ui()
        self.download_button.setEnabled(False)

        # Preview timer
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(150)
        self.preview_timer.timeout.connect(self.update_preview)
        self.paste_text.textChanged.connect(self.preview_timer.start)

    def _setup_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet(STYLESHEET)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)

        # Header
        header = QVBoxLayout()
        header.setSpacing(4)

        title = QLabel('FirstView Downloader')
        title.setObjectName('title')

        subtitle = QLabel('Download runway images from FirstView')
        subtitle.setObjectName('subtitle')

        header.addWidget(title)
        header.addWidget(subtitle)
        main_layout.addLayout(header)

        # URL Input Section
        input_section = QVBoxLayout()
        input_section.setSpacing(8)

        input_label = QLabel('URLS')
        input_label.setObjectName('sectionLabel')

        self.paste_text = PasteEdit()
        self.paste_text.setMinimumHeight(120)
        self.paste_text.setMaximumHeight(160)

        input_section.addWidget(input_label)
        input_section.addWidget(self.paste_text)
        main_layout.addLayout(input_section)

        # Preview Section
        preview_section = QVBoxLayout()
        preview_section.setSpacing(8)

        preview_label = QLabel('PREVIEW')
        preview_label.setObjectName('sectionLabel')

        self.preview_text = QTextEdit()
        self.preview_text.setObjectName('preview')
        self.preview_text.setReadOnly(True)
        self.preview_text.setTextInteractionFlags(Qt.NoTextInteraction)
        self.preview_text.setFocusPolicy(Qt.NoFocus)
        self.preview_text.viewport().setCursor(QCursor(Qt.ArrowCursor))
        self.preview_text.setMinimumHeight(100)
        self.preview_text.setPlaceholderText("Preview will appear here...")

        preview_section.addWidget(preview_label)
        preview_section.addWidget(self.preview_text)
        main_layout.addLayout(preview_section)

        # Progress Section
        self.progress_container = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_container)
        self.progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_layout.setSpacing(8)
        self.progress_container.hide()
        main_layout.addWidget(self.progress_container)

        # Spacer
        main_layout.addStretch()

        # Download Path
        path_section = QVBoxLayout()
        path_section.setSpacing(8)

        path_label = QLabel('SAVE TO')
        path_label.setObjectName('sectionLabel')

        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        default_path = Path.home() / 'Pictures'
        self.path_edit = QLineEdit(str(default_path))
        self.path_edit.setReadOnly(True)

        change_button = QPushButton('Browse')
        change_button.setObjectName('secondary')
        change_button.setFixedWidth(100)
        change_button.clicked.connect(self.change_download_location)

        path_row.addWidget(self.path_edit)
        path_row.addWidget(change_button)

        path_section.addWidget(path_label)
        path_section.addLayout(path_row)
        main_layout.addLayout(path_section)

        # Download Button
        self.download_button = QPushButton('Download')
        self.download_button.setFixedHeight(44)
        self.download_button.clicked.connect(self.download)
        main_layout.addWidget(self.download_button)

        self.setCentralWidget(central)

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
            self.preview_worker.wait()

        self.preview_worker = PreviewWorker(urls, self.preview_cache)
        self.preview_worker.preview_result.connect(self.on_preview_result)
        self.preview_worker.finished.connect(self.on_preview_loaded)
        self.preview_worker.start()

    def on_preview_loaded(self) -> None:
        if not self._has_invalid:
            self.download_button.setEnabled(True)

    def on_preview_result(self, url: str, result: Union[Tuple[str, str, str, str], str]) -> None:
        if result == 'invalid':
            self.preview_text.append(f'<span style="color: {COLORS["error"]};">Unsupported: {url}</span>')
            self._has_invalid = True
        else:
            designer, gender, season, album = result
            parts = [p for p in [designer, gender, season, album] if p]
            display = ' / '.join(parts) if parts else url
            self.preview_text.append(display)

    def download(self) -> None:
        urls = [url.strip() for url in self.paste_text.toPlainText().splitlines() if url.strip()]
        if not urls or self._has_invalid:
            return

        base_path = Path(self.path_edit.text())

        # Check if already in a FirstView folder structure
        path_parts = [p.lower() for p in base_path.parts]
        if 'firstview' in path_parts:
            download_path = base_path
        else:
            download_path = base_path / 'FirstView'

        download_path.mkdir(parents=True, exist_ok=True)

        # Clear progress
        while self.progress_layout.count():
            child = self.progress_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._current_label = None
        self.progress_label = None
        self.progress_bar = None
        self.progress_count = None
        self.progress_container.show()

        self.download_button.setEnabled(False)
        self.download_button.setText('Downloading...')

        self.download_worker = DownloadWorker(urls, download_path)
        self.download_worker.status.connect(self.on_status)
        self.download_worker.error.connect(lambda e: self.preview_text.append(
            f'<span style="color: {COLORS["error"]};">Error: {e}</span>'
        ))
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()

    def on_status(self, message: str) -> None:
        if message.startswith('ERROR:'):
            self.preview_text.append(f'<span style="color: {COLORS["error"]};">{message[6:]}</span>')
            return

        if not message.startswith('PROGRESS:'):
            self.preview_text.append(message)
            return

        _, label, currently_downloaded, total_images = message.split(':')
        current = int(currently_downloaded)
        total = int(total_images)

        if label != self._current_label:
            self._current_label = label

            # Create new progress row
            row = QWidget()
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            # Label and count on same line
            top_row = QHBoxLayout()
            self.progress_label = QLabel(label)
            self.progress_label.setStyleSheet(f'color: {COLORS["text"]}; font-size: 13px;')
            self.progress_count = QLabel(f'0/{total}')
            self.progress_count.setStyleSheet(f'color: {COLORS["text_secondary"]}; font-size: 12px;')
            top_row.addWidget(self.progress_label)
            top_row.addStretch()
            top_row.addWidget(self.progress_count)

            self.progress_bar = QProgressBar()
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setFixedHeight(6)
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(0)

            row_layout.addLayout(top_row)
            row_layout.addWidget(self.progress_bar)

            # Remove old progress if exists
            while self.progress_layout.count():
                child = self.progress_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            self.progress_layout.addWidget(row)

        self.progress_bar.setValue(current)
        self.progress_count.setText(f'{current}/{total}')

    def on_download_finished(self) -> None:
        self.download_button.setEnabled(True)
        self.download_button.setText('Download')

        if self.progress_bar and self.progress_bar.value() == self.progress_bar.maximum():
            self.progress_label.setStyleSheet(f'color: {COLORS["success"]}; font-size: 13px;')


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS['bg']))
    palette.setColor(QPalette.WindowText, QColor(COLORS['text']))
    palette.setColor(QPalette.Base, QColor(COLORS['input_bg']))
    palette.setColor(QPalette.Text, QColor(COLORS['text']))
    palette.setColor(QPalette.Button, QColor(COLORS['card']))
    palette.setColor(QPalette.ButtonText, QColor(COLORS['text']))
    palette.setColor(QPalette.Highlight, QColor(COLORS['accent']))
    app.setPalette(palette)

    icon_file = icon_path('fv.ico')
    app.setWindowIcon(QIcon(icon_file))

    window = MainWindow()
    window.setWindowIcon(QIcon(icon_file))
    window.show()

    sys.exit(app.exec())
