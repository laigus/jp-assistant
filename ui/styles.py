"""QSS styles — premium dark frosted glass UI."""

FONT_STACK = "'Yu Gothic UI', 'Meiryo', 'Microsoft YaHei UI', 'Segoe UI', sans-serif"
FONT_JP = "'Yu Gothic UI', 'Meiryo', 'MS Gothic', sans-serif"

MAIN_STYLE = f"""
* {{
    font-family: {FONT_STACK};
}}

QLabel {{
    color: rgba(255, 255, 255, 165);
    font-size: 13px;
    background: transparent;
}}

QLabel#titleLabel {{
    color: rgba(255, 255, 255, 210);
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 2px;
}}

QLabel#sectionLabel {{
    color: rgba(255, 255, 255, 100);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding-top: 2px;
}}

QLabel#statusLabel {{
    color: rgba(255, 255, 255, 60);
    font-size: 11px;
}}

QTextEdit {{
    background-color: rgba(0, 0, 0, 120);
    color: rgba(255, 255, 255, 210);
    border: 1px solid rgba(255, 255, 255, 6);
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 15px;
    font-family: {FONT_JP};
    selection-background-color: rgba(255, 255, 255, 50);
}}

QTextEdit:focus {{
    border: 1px solid rgba(255, 255, 255, 14);
    background-color: rgba(0, 0, 0, 140);
}}

QTextBrowser {{
    background-color: rgba(0, 0, 0, 100);
    color: rgba(255, 255, 255, 200);
    border: 1px solid rgba(255, 255, 255, 4);
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 14px;
    font-family: {FONT_STACK};
    selection-background-color: rgba(255, 255, 255, 40);
}}

QTextBrowser#resultBrowser {{
    font-size: 15px;
    padding: 10px 14px;
    background-color: rgba(0, 0, 0, 110);
}}

QPushButton {{
    background-color: rgba(0, 0, 0, 80);
    color: rgba(255, 255, 255, 150);
    border: 1px solid rgba(255, 255, 255, 8);
    border-radius: 10px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: rgba(0, 0, 0, 120);
    color: rgba(255, 255, 255, 230);
    border: 1px solid rgba(255, 255, 255, 18);
}}

QPushButton:pressed {{
    background-color: rgba(0, 0, 0, 150);
}}

QPushButton:disabled {{
    background-color: rgba(0, 0, 0, 40);
    color: rgba(255, 255, 255, 35);
    border: 1px solid rgba(255, 255, 255, 3);
}}

QPushButton#captureBtn {{
    background-color: rgba(0, 0, 0, 90);
    font-size: 14px;
    padding: 11px;
    min-height: 22px;
    border: 1px solid rgba(255, 255, 255, 10);
}}

QPushButton#captureBtn:hover {{
    background-color: rgba(0, 0, 0, 130);
    border: 1px solid rgba(255, 255, 255, 22);
}}

QPushButton#closeBtn {{
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 50);
    font-size: 15px;
    padding: 4px 8px;
    border-radius: 8px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}}

QPushButton#closeBtn:hover {{
    background-color: rgba(255, 60, 60, 50);
    color: rgba(255, 120, 120, 200);
}}

QPushButton#minBtn {{
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 50);
    font-size: 15px;
    padding: 4px 8px;
    border-radius: 8px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}}

QPushButton#minBtn:hover {{
    background-color: rgba(255, 255, 255, 12);
    color: rgba(255, 255, 255, 160);
}}

QPushButton#iconBtn {{
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 70);
    font-size: 17px;
    padding: 4px 8px;
    border-radius: 8px;
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
}}

QPushButton#iconBtn:hover {{
    background-color: rgba(255, 255, 255, 10);
    color: rgba(255, 255, 255, 160);
}}

QComboBox {{
    background-color: rgba(0, 0, 0, 80);
    color: rgba(255, 255, 255, 150);
    border: 1px solid rgba(255, 255, 255, 6);
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12px;
    min-height: 22px;
}}

QComboBox:hover {{
    border: 1px solid rgba(255, 255, 255, 14);
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
    border: none;
}}

QComboBox QAbstractItemView {{
    background-color: rgb(22, 22, 28);
    color: rgba(255, 255, 255, 180);
    border: 1px solid rgba(255, 255, 255, 10);
    border-radius: 6px;
    padding: 4px;
    selection-background-color: rgba(255, 255, 255, 15);
    selection-color: rgba(255, 255, 255, 240);
    outline: 0;
    font-size: 12px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 15);
    border-radius: 2px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 30);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
"""
