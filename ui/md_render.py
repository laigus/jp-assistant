"""Markdown to styled HTML conversion with theme-aware colors."""
import re
import markdown

from ui.ui_config import UIConfig


def _css(large: bool = False, font_scale: float = 1.0) -> str:
    """Generate CSS based on current theme (light/dark) with optional font scaling."""
    light = UIConfig().is_light
    if light:
        fg = "rgba(0,0,0,0.80)"
        fg_h1 = "rgba(0,0,0,0.88)"
        fg_h2 = "rgba(0,0,0,0.85)"
        fg_h3 = "rgba(0,0,0,0.75)"
        fg_strong = "rgba(0,0,0,0.92)"
        fg_em = "rgba(0,0,0,0.60)"
        hr_bg = "rgba(0,0,0,0.08)"
        code_bg = "rgba(0,0,0,0.05)"
        th_bg = "rgba(0,0,0,0.04)"
        th_fg = "rgba(0,0,0,0.80)"
        td_border = "rgba(0,0,0,0.10)"
    else:
        fg = "rgba(255,255,255,0.78)"
        fg_h1 = "rgba(255,255,255,0.88)"
        fg_h2 = "rgba(255,255,255,0.85)"
        fg_h3 = "rgba(255,255,255,0.75)"
        fg_strong = "rgba(255,255,255,0.92)"
        fg_em = "rgba(255,255,255,0.68)"
        hr_bg = "rgba(255,255,255,0.06)"
        code_bg = "rgba(255,255,255,0.06)"
        th_bg = "rgba(255,255,255,0.04)"
        th_fg = "rgba(255,255,255,0.80)"
        td_border = "rgba(255,255,255,0.08)"

    def s(px: int) -> int:
        return max(8, int(px * font_scale))

    base = 15 if large else 14

    return f"""
body {{
    color: {fg};
    font-family: 'Yu Gothic UI', 'Meiryo', 'Microsoft YaHei UI', sans-serif;
    font-size: {s(base)}px;
    margin: 0;
    padding: 2px;
}}
h1 {{ color: {fg_h1}; font-size: {s(17)}px; margin-top: 16px; margin-bottom: 6px; }}
h2 {{ color: {fg_h2}; font-size: {s(15)}px; margin-top: 14px; margin-bottom: 4px; }}
h3 {{ color: {fg_h3}; font-size: {s(14)}px; margin-top: 10px; margin-bottom: 2px; }}
strong, b {{ color: {fg_strong}; }}
em, i {{ color: {fg_em}; }}
ul, ol {{ padding-left: 22px; margin-top: 2px; margin-bottom: 2px; }}
li {{ margin-top: 2px; margin-bottom: 2px; }}
p {{ margin-top: 4px; margin-bottom: 4px; }}
hr {{ border: none; height: 1px; background: {hr_bg}; margin: 10px 0; }}
code {{
    background: {code_bg};
    padding: 1px 4px;
    border-radius: 3px;
    font-family: 'Consolas', 'MS Gothic', monospace;
    font-size: {s(13)}px;
}}
table {{ border-collapse: collapse; margin: 6px 0; }}
th, td {{ border: 1px solid {td_border}; padding: 3px 8px; }}
th {{ background: {th_bg}; color: {th_fg}; }}
"""


def _preprocess(text: str) -> str:
    """Ensure Chinese-style section headers and list formatting."""
    text = re.sub(
        r'^([一二三四五六七八九十]+、.+)$',
        r'## \1',
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r'^(## )+', '## ', text, flags=re.MULTILINE)

    # Ensure blank line before list items that follow non-list content
    # This ensures Markdown parser treats them as proper list items
    text = re.sub(r'(\S)\n(- )', r'\1\n\n\2', text)

    return text


def md_to_html(md_text: str, large: bool = False, font_scale: float = 1.0) -> str:
    processed = _preprocess(md_text)
    body = markdown.markdown(
        processed,
        extensions=["tables", "sane_lists"],
    )
    css = _css(large, font_scale)
    return f"<html><head><style>{css}</style></head><body>{body}</body></html>"
