"""Build the Windows icon from the bundled application artwork."""
from pathlib import Path

from PIL import Image

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def create_icon(icon_path: str):
    assets_dir = Path(__file__).resolve().parent
    source_path = assets_dir / "app.png"
    with Image.open(source_path) as source:
        if source.width != source.height:
            raise ValueError("Application artwork must be square")
        image = source.convert("RGBA")
        if image.getchannel("A").getextrema()[0] == 255:
            raise ValueError("Application artwork must retain transparent rounded corners")
        image.save(
            icon_path, format="ICO", sizes=[(size, size) for size in ICON_SIZES]
        )
    return str(icon_path)
