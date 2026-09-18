"""Gera o ícone do RPG Audio Studio (item 10 da Etapa 6).

Solução temporária consistente com o tema escuro do app (fundo escuro +
cor de destaque azul) — um disco de reprodução estilizado com uma nota
musical. Se um ícone definitivo (feito por um designer) existir no
futuro, é só substituir ``assets/icon.ico`` e ``assets/icon.png`` — nada
mais no código precisa mudar, os dois nomes de arquivo já são o que o app
e o ``.spec`` do PyInstaller esperam.

Uso:
    python scripts/generate_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

BG_DARK = (26, 29, 35, 255)       # mesmo #1a1d23 do tema escuro compartilhado
ACCENT = (91, 140, 255, 255)      # mesmo #5b8cff do accent padrão
NOTE_COLOR = (232, 233, 236, 255)  # mesmo #e8e9ec (texto primário do tema)

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _draw_icon(size: int) -> Image.Image:
    # Desenha em 4x o tamanho final e reduz depois (antialiasing simples).
    scale = 4
    canvas_size = size * scale
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    margin = canvas_size * 0.06
    radius = canvas_size * 0.22
    draw.rounded_rectangle(
        [margin, margin, canvas_size - margin, canvas_size - margin],
        radius=radius, fill=BG_DARK,
    )

    # Disco/círculo de destaque
    circle_margin = canvas_size * 0.20
    draw.ellipse(
        [circle_margin, circle_margin, canvas_size - circle_margin, canvas_size - circle_margin],
        fill=ACCENT,
    )

    # Nota musical simples (cabeça + haste), em cima do círculo
    cx, cy = canvas_size / 2, canvas_size / 2
    head_w, head_h = canvas_size * 0.16, canvas_size * 0.12
    head_x, head_y = cx - canvas_size * 0.04, cy + canvas_size * 0.10
    draw.ellipse(
        [head_x - head_w / 2, head_y - head_h / 2, head_x + head_w / 2, head_y + head_h / 2],
        fill=NOTE_COLOR,
    )
    stem_w = canvas_size * 0.035
    stem_top = cy - canvas_size * 0.22
    draw.rectangle(
        [head_x + head_w / 2 - stem_w, stem_top, head_x + head_w / 2, head_y],
        fill=NOTE_COLOR,
    )
    flag_points = [
        (head_x + head_w / 2, stem_top),
        (head_x + head_w / 2 + canvas_size * 0.14, stem_top + canvas_size * 0.10),
        (head_x + head_w / 2, stem_top + canvas_size * 0.16),
    ]
    draw.polygon(flag_points, fill=NOTE_COLOR)

    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    png_path = ASSETS_DIR / "icon.png"
    _draw_icon(512).save(png_path)
    print(f"Gerado: {png_path}")

    ico_path = ASSETS_DIR / "icon.ico"
    images = [_draw_icon(s) for s in ICO_SIZES]
    images[0].save(
        ico_path, format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=images[1:],
    )
    print(f"Gerado: {ico_path}")


if __name__ == "__main__":
    main()
