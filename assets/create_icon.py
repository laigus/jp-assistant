"""Generate app icon for JP Assistant."""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    sizes = [256, 128, 64, 48, 32, 16]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        pad = max(1, size // 16)
        r = size // 6

        # Dark gradient-like rounded rect background
        draw.rounded_rectangle(
            [pad, pad, size - pad - 1, size - pad - 1],
            radius=r,
            fill=(30, 36, 60, 240),
        )

        # Subtle inner highlight
        draw.rounded_rectangle(
            [pad + 1, pad + 1, size - pad - 2, size - pad - 2],
            radius=r - 1,
            fill=None,
            outline=(100, 140, 255, 50),
            width=max(1, size // 64),
        )

        # Draw "JP" text
        font_size = int(size * 0.42)
        try:
            font = ImageFont.truetype("Yu Gothic Bold", font_size)
        except OSError:
            try:
                font = ImageFont.truetype("meiryo", font_size)
            except OSError:
                try:
                    font = ImageFont.truetype("arial", font_size)
                except OSError:
                    font = ImageFont.load_default()

        text = "JP"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = (size - tw) // 2 - bbox[0]
        ty = (size - th) // 2 - bbox[1] - int(size * 0.04)
        draw.text((tx, ty), text, fill=(130, 180, 255, 255), font=font)

        # Small "日本語" subtitle for larger sizes
        if size >= 48:
            sub_size = max(8, int(size * 0.16))
            try:
                sub_font = ImageFont.truetype("Yu Gothic", sub_size)
            except OSError:
                try:
                    sub_font = ImageFont.truetype("meiryo", sub_size)
                except OSError:
                    sub_font = None

            if sub_font:
                sub = "日本語"
                sb = draw.textbbox((0, 0), sub, font=sub_font)
                sw = sb[2] - sb[0]
                sx = (size - sw) // 2 - sb[0]
                sy = ty + th + int(size * 0.02)
                draw.text((sx, sy), sub, fill=(180, 200, 255, 180), font=sub_font)

        images.append(img)

    icon_path = os.path.join(os.path.dirname(__file__), "app.ico")
    images[0].save(
        icon_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"Icon saved to {icon_path}")
    return icon_path


if __name__ == "__main__":
    create_icon()
