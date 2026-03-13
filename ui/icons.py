"""SVG icon rendering for clean, scalable UI icons with theme-aware colors."""
from PyQt6.QtCore import QByteArray, QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtSvg import QSvgRenderer

# SVG path data for each icon (24x24 viewBox)
_ICONS = {
    "settings": (
        '<path d="M12 15.5A3.5 3.5 0 0 1 8.5 12 3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 '
        '3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97s-.03-.66-.07-1l'
        '2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-'
        '.4-1.08-.73-1.69-.98l-.38-2.65A.49.49 0 0 0 14 2h-4c-.25 0-.46.18-.49.42l-'
        '.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13'
        '.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1s.03.65.07.97l-2.11 1.66c-.19.15'
        '-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.08.73 1.69.98l.38 '
        '2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.58 1.69'
        '-.98l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64z"/>'
    ),
    "capture": (
        '<path d="M3 3h5V1H1v7h2zm0 18h5v2H1v-7h2zm18-18h-5V1h7v7h-2zm0 18h-5v2h7v-7h-2z"/>'
        '<rect x="7" y="7" width="10" height="10" rx="1.5" fill="none" stroke-width="1.5"/>'
    ),
    "analyze": (
        '<circle cx="11" cy="11" r="6" fill="none" stroke-width="2"/>'
        '<line x1="16.5" y1="16.5" x2="21" y2="21" stroke-width="2" stroke-linecap="round"/>'
        '<path d="M9 11h4M11 9v4" stroke-width="1.5" stroke-linecap="round"/>'
    ),
    "speak": (
        '<polygon points="6,4 6,20 18,12"/>'
    ),
    "expand": (
        '<polyline points="15 3 21 3 21 9" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<polyline points="9 21 3 21 3 15" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<line x1="21" y1="3" x2="14" y2="10" stroke-width="2" stroke-linecap="round"/>'
        '<line x1="3" y1="21" x2="10" y2="14" stroke-width="2" stroke-linecap="round"/>'
    ),
    "minimize": (
        '<line x1="5" y1="12" x2="19" y2="12" stroke-width="2" stroke-linecap="round"/>'
    ),
    "close": (
        '<line x1="6" y1="6" x2="18" y2="18" stroke-width="2" stroke-linecap="round"/>'
        '<line x1="18" y1="6" x2="6" y2="18" stroke-width="2" stroke-linecap="round"/>'
    ),
}


def _build_svg(name: str, color: str) -> bytes:
    """Build a complete SVG document from icon path data."""
    paths = _ICONS.get(name, "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="{color}" stroke="{color}">'
        f'{paths}</svg>'
    ).encode("utf-8")


def icon(name: str, size: int = 18, color: str = "#ffffff") -> QIcon:
    """Render a named icon as QIcon at the given size and color."""
    svg_data = _build_svg(name, color)
    renderer = QSvgRenderer(QByteArray(svg_data))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    from PyQt6.QtGui import QPainter
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def themed_color(is_light: bool, alpha: float = 0.7) -> str:
    """Return an appropriate icon color string for the theme."""
    if is_light:
        a = int(alpha * 255)
        return f"rgba(0,0,0,{a/255:.2f})"
    else:
        a = int(alpha * 255)
        return f"rgba(255,255,255,{a/255:.2f})"


def icon_color_hex(is_light: bool) -> str:
    """Return hex color for icons based on theme."""
    return "#000000" if is_light else "#ffffff"
