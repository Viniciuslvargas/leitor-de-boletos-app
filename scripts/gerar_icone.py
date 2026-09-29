from pathlib import Path

from PIL import Image, ImageDraw

DESTINO = Path(__file__).resolve().parent.parent / "src" / "leitor_boletos" / "dados" / "icone.ico"
AZUL = (31, 106, 165, 255)
BRANCO = (255, 255, 255, 255)


def desenhar(tamanho: int = 256) -> Image.Image:
    img = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = tamanho / 16
    d.rounded_rectangle((1 * u, 1 * u, 15 * u, 15 * u), radius=3 * u, fill=AZUL)
    d.rounded_rectangle((4 * u, 3 * u, 12 * u, 13 * u), radius=0.8 * u, fill=BRANCO)
    for y in (5.5, 7.5, 9.5):
        d.rectangle((5.5 * u, y * u, 10.5 * u, (y + 0.7) * u), fill=AZUL)
    larguras = [0.35, 0.15, 0.15, 0.35, 0.15, 0.35, 0.15, 0.15, 0.35, 0.15, 0.35]
    x = 5.5
    for largura in larguras:
        d.rectangle((x * u, 10.9 * u, (x + largura) * u, 12.3 * u), fill=AZUL)
        x += largura + 0.2
    return img


if __name__ == "__main__":
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    desenhar().save(DESTINO, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icone gravado em", DESTINO)
