#!/usr/bin/env python3
"""
Gera ícones para o PWA quantum
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    """Cria um ícone com fundo preto e texto Q com gradiente"""
    # Cria imagem com fundo preto
    img = Image.new('RGB', (size, size), color=(15, 15, 35))
    
    # Cria imagem com gradiente para o texto
    gradient = Image.new('RGB', (size, size))
    draw_gradient = ImageDraw.Draw(gradient)
    
    # Gradiente roxo/rosa
    for y in range(size):
        r = int(139 + (236 - 139) * y / size)
        g = int(92 + (72 - 92) * y / size)
        b = int(246 + (153 - 246) * y / size)
        draw_gradient.line([(0, y), (size, y)], fill=(r, g, b))
    
    # Cria máscara com o texto "Q"
    mask = Image.new('L', (size, size), 0)
    draw_mask = ImageDraw.Draw(mask)
    
    try:
        font_size = int(size * 0.6)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    text = "Q"
    bbox = draw_mask.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]
    
    # Desenha o texto na máscara
    draw_mask.text((x, y), text, font=font, fill=255)
    
    # Aplica o gradiente usando a máscara
    img.paste(gradient, (0, 0), mask)
    
    img.save(filename, 'PNG')
    print(f"✓ Criado: {filename}")

if __name__ == '__main__':
    create_icon(192, 'icon-192.png')
    create_icon(512, 'icon-512.png')
    print("\n✅ Ícones criados com sucesso!")
