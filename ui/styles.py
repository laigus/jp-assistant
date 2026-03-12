"""QSS styles for the frosted glass UI."""

MAIN_STYLE = """
QLabel {
    color: #d8e4f0;
    font-size: 13px;
    background: transparent;
}

QLabel#titleLabel {
    color: #88ccff;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 2px;
}

QLabel#sectionLabel {
    color: #7ab8e0;
    font-size: 12px;
    font-weight: bold;
    padding-top: 2px;
}

QLabel#statusLabel {
    color: #556677;
    font-size: 11px;
}

QTextEdit {
    background-color: rgba(255, 255, 255, 10);
    color: #f0f4f8;
    border: 1px solid rgba(136, 204, 255, 35);
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 16px;
    font-family: "Yu Gothic UI", "Meiryo", "Microsoft YaHei", sans-serif;
    selection-background-color: rgba(136, 204, 255, 80);
}

QTextEdit:focus {
    border: 1px solid rgba(136, 204, 255, 90);
}

QTextEdit#analysisArea {
    font-size: 13px;
    line-height: 1.6;
    background-color: rgba(255, 255, 255, 6);
    border: 1px solid rgba(136, 204, 255, 18);
}

QPushButton {
    background-color: rgba(136, 204, 255, 18);
    color: #b8d4e8;
    border: 1px solid rgba(136, 204, 255, 35);
    border-radius: 10px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: rgba(136, 204, 255, 45);
    color: #ffffff;
    border: 1px solid rgba(136, 204, 255, 90);
}

QPushButton:pressed {
    background-color: rgba(136, 204, 255, 65);
}

QPushButton:disabled {
    background-color: rgba(60, 60, 80, 20);
    color: #445566;
    border: 1px solid rgba(60, 60, 80, 20);
}

QPushButton#captureBtn {
    background-color: rgba(136, 204, 255, 28);
    font-size: 14px;
    padding: 11px;
    min-height: 22px;
    border: 1px solid rgba(136, 204, 255, 50);
}

QPushButton#captureBtn:hover {
    background-color: rgba(136, 204, 255, 55);
    border: 1px solid rgba(136, 204, 255, 120);
}

QPushButton#closeBtn {
    background: transparent;
    border: none;
    color: #556677;
    font-size: 14px;
    padding: 2px 6px;
    border-radius: 6px;
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
}

QPushButton#closeBtn:hover {
    background-color: rgba(255, 70, 70, 60);
    color: #ff8888;
}

QPushButton#minBtn {
    background: transparent;
    border: none;
    color: #556677;
    font-size: 14px;
    padding: 2px 6px;
    border-radius: 6px;
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
}

QPushButton#minBtn:hover {
    background-color: rgba(136, 204, 255, 30);
    color: #88ccff;
}

QScrollBar:vertical {
    background: transparent;
    width: 5px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(136, 204, 255, 35);
    border-radius: 2px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(136, 204, 255, 70);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
"""
