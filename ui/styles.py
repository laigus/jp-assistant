"""QSS styles — dynamic opacity and theme support (dark/light)."""

FONT_STACK = "'Yu Gothic UI', 'Meiryo', 'Microsoft YaHei UI', 'Segoe UI', sans-serif"
FONT_JP = "'Yu Gothic UI', 'Meiryo', 'MS Gothic', sans-serif"


def build_style(opacity: int = 15, is_light: bool = False) -> str:
    """Generate QSS with widget backgrounds scaled by opacity (0-100)."""
    t = max(0, min(100, opacity)) / 100.0

    if is_light:
        # Light theme: white/light backgrounds, dark text
        fg = "rgba(0, 0, 0, 200)"
        fg_title = "rgba(0, 0, 0, 230)"
        fg_section = "rgba(0, 0, 0, 100)"
        fg_status = "rgba(0, 0, 0, 80)"
        fg_dim = "rgba(0, 0, 0, 130)"
        fg_btn_hover = "rgba(0, 0, 0, 240)"
        fg_disabled = "rgba(0, 0, 0, 60)"
        sel_bg = "rgba(0, 100, 200, 50)"
        border = "rgba(0, 0, 0, 8)"
        border_focus = "rgba(0, 0, 0, 18)"
        border_hover = "rgba(0, 0, 0, 20)"
        close_hover_bg = "rgba(255, 60, 60, 40)"
        close_hover_fg = "rgba(220, 50, 50, 200)"
        min_hover_bg = "rgba(0, 0, 0, 8)"
        min_hover_fg = "rgba(0, 0, 0, 150)"
        icon_fg = "rgba(0, 0, 0, 60)"
        icon_hover_bg = "rgba(0, 0, 0, 8)"
        icon_hover_fg = "rgba(0, 0, 0, 150)"
        slider_groove = "rgba(0, 0, 0, 12)"
        slider_handle = "rgba(0, 0, 0, 100)"
        slider_handle_hover = "rgba(0, 0, 0, 160)"
        slider_sub = "rgba(0, 100, 200, 40)"
        scroll_handle = "rgba(0, 0, 0, 15)"
        scroll_hover = "rgba(0, 0, 0, 30)"
        # backgrounds — white tinted (high min alpha so cursor stays visible)
        bg_base = "255, 255, 255"
        te_bg = int(200 + t * 45)
        te_focus = int(220 + t * 30)
        tb_bg = int(25 + t * 75)
        tb_result = int(30 + t * 80)
        btn_bg = int(15 + t * 50)
        btn_hover = int(25 + t * 70)
        btn_press = int(35 + t * 90)
        cap_bg = int(20 + t * 55)
        cap_hover = int(30 + t * 80)
        cb_bg = int(15 + t * 50)
        cb_view = f"rgb({int(240 + t * 10)}, {int(240 + t * 10)}, {int(245 + t * 5)})"
    else:
        # Dark theme: black backgrounds, white text
        fg = "rgba(255, 255, 255, 210)"
        fg_title = "rgba(255, 255, 255, 210)"
        fg_section = "rgba(255, 255, 255, 100)"
        fg_status = "rgba(255, 255, 255, 60)"
        fg_dim = "rgba(255, 255, 255, 150)"
        fg_btn_hover = "rgba(255, 255, 255, 230)"
        fg_disabled = "rgba(255, 255, 255, 35)"
        sel_bg = "rgba(255, 255, 255, 50)"
        border = "rgba(255, 255, 255, 6)"
        border_focus = "rgba(255, 255, 255, 14)"
        border_hover = "rgba(255, 255, 255, 18)"
        close_hover_bg = "rgba(255, 60, 60, 50)"
        close_hover_fg = "rgba(255, 120, 120, 200)"
        min_hover_bg = "rgba(255, 255, 255, 12)"
        min_hover_fg = "rgba(255, 255, 255, 160)"
        icon_fg = "rgba(255, 255, 255, 70)"
        icon_hover_bg = "rgba(255, 255, 255, 10)"
        icon_hover_fg = "rgba(255, 255, 255, 160)"
        slider_groove = "rgba(255, 255, 255, 10)"
        slider_handle = "rgba(255, 255, 255, 120)"
        slider_handle_hover = "rgba(255, 255, 255, 180)"
        slider_sub = "rgba(255, 255, 255, 30)"
        scroll_handle = "rgba(255, 255, 255, 15)"
        scroll_hover = "rgba(255, 255, 255, 30)"
        bg_base = "0, 0, 0"
        te_bg = int(30 + t * 90)
        te_focus = int(40 + t * 100)
        tb_bg = int(25 + t * 75)
        tb_result = int(30 + t * 80)
        btn_bg = int(20 + t * 60)
        btn_hover = int(30 + t * 90)
        btn_press = int(40 + t * 110)
        cap_bg = int(25 + t * 65)
        cap_hover = int(35 + t * 95)
        cb_bg = int(20 + t * 60)
        cb_view = f"rgb({int(10 + t * 12)}, {int(10 + t * 12)}, {int(14 + t * 14)})"

    return f"""
* {{
    font-family: {FONT_STACK};
}}

QLabel {{
    color: {fg};
    font-size: 13px;
    background: transparent;
}}

QLabel#titleLabel {{
    color: {fg_title};
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 2px;
}}

QLabel#sectionLabel {{
    color: {fg_section};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding-top: 2px;
}}

QLabel#statusLabel {{
    color: {fg_status};
    font-size: 11px;
}}

QTextEdit {{
    background-color: rgba({bg_base}, {te_bg});
    color: {fg};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 15px;
    font-family: {FONT_JP};
    selection-background-color: {sel_bg};
}}

QTextEdit:focus {{
    border: 1px solid {border_focus};
    background-color: rgba({bg_base}, {te_focus});
}}

QTextBrowser {{
    background-color: rgba({bg_base}, {tb_bg});
    color: {fg};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 14px;
    font-family: {FONT_STACK};
    selection-background-color: {sel_bg};
}}

QTextBrowser:focus {{
    border: 1px solid {border_focus};
    background-color: rgba({bg_base}, {int(tb_bg + 5)});
}}

QTextBrowser#resultBrowser {{
    font-size: 15px;
    padding: 10px 14px;
    background-color: rgba({bg_base}, {tb_result});
}}

QTextBrowser#resultBrowser:focus {{
    background-color: rgba({bg_base}, {int(tb_result + 5)});
}}

QPushButton {{
    background-color: rgba({bg_base}, {btn_bg});
    color: {fg_dim};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: rgba({bg_base}, {btn_hover});
    color: {fg_btn_hover};
    border: 1px solid {border_hover};
}}

QPushButton:pressed {{
    background-color: rgba({bg_base}, {btn_press});
}}

QPushButton:disabled {{
    background-color: rgba({bg_base}, 40);
    color: {fg_disabled};
    border: 1px solid rgba({bg_base}, 10);
}}

QPushButton#captureBtn {{
    background-color: rgba({bg_base}, {cap_bg});
    font-size: 14px;
    padding: 11px;
    min-height: 22px;
    border: 1px solid {border};
}}

QPushButton#captureBtn:hover {{
    background-color: rgba({bg_base}, {cap_hover});
    border: 1px solid {border_hover};
}}

QPushButton#closeBtn {{
    background: transparent;
    border: none;
    color: {fg_status};
    font-size: 15px;
    padding: 4px 8px;
    border-radius: 8px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}}

QPushButton#closeBtn:hover {{
    background-color: {close_hover_bg};
    color: {close_hover_fg};
}}

QPushButton#minBtn {{
    background: transparent;
    border: none;
    color: {fg_status};
    font-size: 15px;
    padding: 4px 8px;
    border-radius: 8px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}}

QPushButton#minBtn:hover {{
    background-color: {min_hover_bg};
    color: {min_hover_fg};
}}

QPushButton#iconBtn {{
    background: transparent;
    border: none;
    color: {icon_fg};
    font-size: 17px;
    padding: 4px 8px;
    border-radius: 8px;
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
}}

QPushButton#iconBtn:hover {{
    background-color: {icon_hover_bg};
    color: {icon_hover_fg};
}}

QComboBox {{
    background-color: rgba({bg_base}, {cb_bg});
    color: {fg_dim};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12px;
    min-height: 22px;
}}

QComboBox:hover {{
    border: 1px solid {border_focus};
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
    background-color: {cb_view};
    color: {fg};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {sel_bg};
    selection-color: {fg_btn_hover};
    outline: 0;
    font-size: 12px;
}}

QSlider::groove:horizontal {{
    background: {slider_groove};
    height: 4px;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {slider_handle};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: {slider_handle_hover};
}}

QSlider::sub-page:horizontal {{
    background: {slider_sub};
    border-radius: 2px;
}}

QCheckBox {{
    color: {fg};
    font-size: 12px;
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {border};
    background: rgba({bg_base}, {int(20 + t * 40)});
}}

QCheckBox::indicator:checked {{
    background: {slider_handle};
    border: 1px solid {border_focus};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {scroll_handle};
    border-radius: 2px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {scroll_hover};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QWidget#vocabCard {{
    background-color: rgba({bg_base}, {btn_bg});
    border: 1px solid {border};
    border-radius: 10px;
    padding: 2px;
}}

QWidget#vocabCard:hover {{
    background-color: rgba({bg_base}, {btn_hover});
    border: 1px solid {border_hover};
}}
"""


MAIN_STYLE = build_style(15)
