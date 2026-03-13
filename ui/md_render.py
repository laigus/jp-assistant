"""Markdown to styled HTML conversion for dark-themed QTextBrowser."""
import re
import markdown

MD_CSS = """
body {
    color: rgba(255,255,255,0.78);
    font-family: 'Yu Gothic UI', 'Meiryo', 'Microsoft YaHei UI', sans-serif;
    font-size: 14px;
    margin: 0;
    padding: 2px;
}
h1 { color: rgba(255,255,255,0.88); font-size: 17px; margin-top: 16px; margin-bottom: 6px; }
h2 { color: rgba(255,255,255,0.85); font-size: 15px; margin-top: 14px; margin-bottom: 4px; }
h3 { color: rgba(255,255,255,0.75); font-size: 14px; margin-top: 10px; margin-bottom: 2px; }
strong, b { color: rgba(255,255,255,0.92); }
em, i { color: rgba(255,255,255,0.68); }
ul, ol { padding-left: 22px; margin-top: 2px; margin-bottom: 2px; }
li { margin-top: 2px; margin-bottom: 2px; }
p { margin-top: 4px; margin-bottom: 4px; }
hr { border: none; height: 1px; background: rgba(255,255,255,0.06); margin: 10px 0; }
code {
    background: rgba(255,255,255,0.06);
    padding: 1px 4px;
    border-radius: 3px;
    font-family: 'Consolas', 'MS Gothic', monospace;
    font-size: 13px;
}
table { border-collapse: collapse; margin: 6px 0; }
th, td { border: 1px solid rgba(255,255,255,0.08); padding: 3px 8px; }
th { background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.8); }
"""

MD_CSS_LARGE = MD_CSS.replace("font-size: 14px", "font-size: 15px")


def _preprocess(text: str) -> str:
    """Ensure Chinese-style section headers become markdown headers."""
    text = re.sub(
        r'^([一二三四五六七八九十]+、.+)$',
        r'## \1',
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r'^(## )+', '## ', text, flags=re.MULTILINE)
    return text


def md_to_html(md_text: str, large: bool = False) -> str:
    processed = _preprocess(md_text)
    body = markdown.markdown(
        processed,
        extensions=["tables", "sane_lists"],
    )
    css = MD_CSS_LARGE if large else MD_CSS
    return f"<html><head><style>{css}</style></head><body>{body}</body></html>"
