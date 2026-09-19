r"""Vẽ PNG icon từ toạ độ logo B (docs/icons/logo.svg) — không cần cairosvg.
Chạy: venv\Scripts\python -m scripts.make_icons   (cần Pillow, chỉ dùng trên máy dev)."""
from pathlib import Path

from PIL import Image, ImageDraw

INK, CREAM, GOLD = (0x1F, 0x3A, 0x2E), (0xF7, 0xF4, 0xEC), (0xC9, 0x9A, 0x2E)
OUT = Path(__file__).resolve().parent.parent / "docs" / "icons"


def draw(size: int, maskable: bool) -> Image.Image:
    # Vẽ ở 4× rồi thu nhỏ để nét mượt. Maskable: nền phủ kín, hình thu vào vùng an toàn 80 %.
    S = size * 4
    img = Image.new("RGBA", (S, S), INK if maskable else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if not maskable:
        d.rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 28 / 120), fill=INK)
    k = (S * 0.8 / 120) if maskable else (S / 120)
    off = (S - 120 * k) / 2

    def P(x, y):
        return (off + x * k, off + y * k)

    def vline(x, y1, y2, col, w):
        d.line([P(x, y1), P(x, y2)], fill=col, width=int(w * k))
        r = w * k / 2
        for y in (y1, y2):
            cx, cy = P(x, y)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)

    def rect(x, y, w, h, col, outline=None, width=0):
        x1, y1 = P(x, y)
        x2, y2 = P(x + w, y + h)
        if outline:
            # Thân rỗng: tô nền để che râu chạy qua, rồi viền
            d.rounded_rectangle((x1, y1, x2, y2), radius=int(2 * k), fill=INK, outline=outline, width=int(width * k))
        else:
            d.rounded_rectangle((x1, y1, x2, y2), radius=int(2 * k), fill=col)

    vline(30, 24, 80, CREAM, 7)
    rect(20, 34, 20, 30, None, outline=CREAM, width=6)
    vline(60, 64, 90, CREAM, 7)
    rect(50, 72, 20, 9, CREAM)
    vline(90, 26, 84, GOLD, 7)
    rect(80, 36, 20, 34, GOLD)
    base = tuple(int(a * 0.45 + b * 0.55) for a, b in zip(CREAM, INK))
    d.line([P(16, 100), P(104, 100)], fill=base, width=int(3 * k))
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw(192, False).save(OUT / "icon-192.png")
    draw(512, False).save(OUT / "icon-512.png")
    draw(512, True).convert("RGB").save(OUT / "icon-maskable.png")
    print("wrote icon-192.png, icon-512.png, icon-maskable.png ->", OUT)


if __name__ == "__main__":
    main()
