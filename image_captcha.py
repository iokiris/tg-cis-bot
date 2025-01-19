import io
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import utils


def generate_captcha_image() -> (io.BytesIO, str):
    captcha_text = utils.gen_captcha_key()

    # Конфиг изображения
    width, height = 200, 70
    background_color = (255, 255, 255)
    text_color = (0, 0, 0)
    font_size = 36

    image = Image.new('RGB', (width, height), color=background_color)
    draw = ImageDraw.Draw(image)

    # Шрифт
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    text_images = []
    total_text_width = 0

    for char in captcha_text:
        # Создание места для каждого символа
        char_image = Image.new('RGBA', (font_size, font_size), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_image)
        char_draw.text((0, 0), char, font=font, fill=text_color)

        bbox = char_draw.textbbox((0, 0), char, font=font)
        char_width = bbox[2] - bbox[0]
        char_height = bbox[3] - bbox[1]

        total_text_width += char_width
        text_images.append((char_image, char_width, char_height))

    text_x = (width - total_text_width) // 2
    text_y = (height - max(char_height for _, _, char_height in text_images)) // 2

    # Текст
    for char_image, char_width, char_height in text_images:
        angle = random.randint(-10, 10)  # Уменьшенный диапазон углов
        char_image = char_image.rotate(angle, resample=Image.BICUBIC)
        image.paste(char_image, (text_x, text_y), char_image)
        text_x += char_width  # смещение для следующих букв

    # линии и точки
    for _ in range(random.randint(20, 40)):
        line_x1 = random.randint(0, width)
        line_y1 = random.randint(0, height)
        line_x2 = random.randint(0, width)
        line_y2 = random.randint(0, height)
        draw.line((line_x1, line_y1, line_x2, line_y2), fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)), width=1)

    for _ in range(random.randint(20, 40)):
        draw.point((random.randint(0, width), random.randint(0, height)), fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)))

    # шум
    image = image.filter(ImageFilter.GaussianBlur(0.5))

    bio = io.BytesIO()
    image.save(bio, format='PNG')
    bio.seek(0)

    return bio, captcha_text


if __name__ == "__main__":
    bio, text = generate_captcha_image()
    print(f"Captcha text: {text}")
