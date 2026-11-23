"""Local paper, charcoal, typography and original soundtrack."""
from functools import lru_cache
import math
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

SIZE = (1920, 1080)
W, H = SIZE


def hex_rgb(color):
    return tuple(bytes.fromhex(color.lstrip('#')))


@lru_cache(maxsize=32)
def font(family, size, bold=False):
    path = subprocess.check_output(
        ['fc-match', '-f', '%{file}', family + (':style=Bold' if bold else '')], text=True
    )
    return ImageFont.truetype(path, size)


def text(draw, position, label, config, size, color, serif=False, bold=False, **kwargs):
    face = config['fonts']['serif' if serif else 'sans']
    draw.text(position, label, font=font(face, size, bold), fill=color, **kwargs)


@lru_cache(maxsize=4)
def paper(base, dark):
    rng = np.random.default_rng(2026)
    y, x = np.ogrid[-1:1:1080j, -1:1:1920j]
    grain = rng.normal(0, 3.7 if dark else 4.0, (H, W)) - 13 * (x*x + y*y)
    return Image.fromarray(np.uint8(np.clip(np.array(base) + grain[:,:,None], 0, 255)))


def charcoal(frame, config):
    frame = ImageOps.fit(frame, (900, 650), centering=(0.5, 0.4))
    gray = ImageOps.autocontrast(frame.convert('L'), cutoff=1)
    blur = np.asarray(ImageOps.invert(gray).filter(ImageFilter.GaussianBlur(10)), dtype=float)
    pencil = np.asarray(gray, dtype=float) * 255 / np.maximum(255 - blur, 1)
    edges = np.asarray(gray.filter(ImageFilter.FIND_EDGES), dtype=float)
    shade = np.clip(50 + 0.54*pencil + 0.4*np.asarray(gray) - 0.63*edges, 0, 255)
    y, x = np.indices(shade.shape)
    hatch = np.where(((x+2*y) % 15 < 2) & (shade < 155), 15, 0)
    mask = Image.fromarray(np.uint8(np.clip(255-shade+hatch, 0, 255)))
    return ImageOps.colorize(mask, config['palette']['ivory'], config['palette']['coal'])


def tunnel(draw, config, progress):
    rng = np.random.default_rng(1748)
    center = np.array([1470, 460])
    for depth in range(14):
        radius = 1060 * (0.83 ** depth) * (1.0 + 0.04 * progress)
        angle = np.linspace(0, math.tau, 66)
        distort = 1 + .07*np.sin(3*angle+depth*.4) + .035*np.cos(7*angle+depth)
        points = np.stack([np.cos(angle)*radius*distort, np.sin(angle)*radius*distort*.83], axis=1) + center
        for n in range(6):
            rough = points + rng.normal(0, 2+n*1.4, points.shape)
            stops = min(len(rough), round(len(rough)*min(1, .28+progress)))
            ink = (154, 89, 72) if depth in (3, 8) and n == 0 else (65+n*4, 63+n*3, 64+n*3)
            draw.line(list(map(tuple, rough[:stops])), fill=ink, width=1+(n<2))


def card(config, item, progress=1, portrait=None):
    colors = config['palette']
    dark = item['card'] in ('open', 'close', 'end')
    image = paper(hex_rgb(colors['coal' if dark else 'ivory']), dark).copy()
    draw = ImageDraw.Draw(image)
    ivory, coal, rust = colors['ivory'], colors['coal'], colors['rust']
    if dark:
        tunnel(draw, config, progress)
        gradient = np.uint8(np.clip((1220-np.arange(W))*0.18, 0, 160))
        overlay = Image.new('RGB', SIZE, colors['coal'])
        image.paste(overlay, mask=Image.fromarray(np.tile(gradient, (H,1))))
        draw = ImageDraw.Draw(image)
    else:
        draw.rectangle((0, 0, 26, H), fill=rust)
        draw.line((128, 939, 1792, 939), fill=colors['slate'], width=2)
        text(draw, (130, 970), config['institution'], config, 25, coal)
        if portrait is not None:
            image.paste(charcoal(portrait, config).resize((650,469)), (1154,288))
            draw.rectangle((1153,287,1804,758), outline=coal, width=1)

    kind = item['card']
    if kind == 'open':
        text(draw, (128, 142), config['institution'].upper(), config, 31, ivory, bold=True)
        draw.rectangle((133, 320, 249, 329), fill=rust)
        text(draw, (117, 354), config['title'], config, 183, ivory, serif=True)
        text(draw, (132, 594), config['subtitle'], config, 54, ivory)
        text(draw, (133, 873), config['edition'], config, 29, ivory)
    elif kind in ('close','end'):
        text(draw, (129, 176), config['institution'].upper(), config, 31, ivory, bold=True)
        draw.rectangle((130, 319, 246, 327), fill=rust)
        text(draw, (120, 349), config['title'], config, 120, ivory, serif=True)
        text(draw, (130, 525), 'Conversación literaria · 2026', config, 42, ivory)
        names = [person['name'] for person in config['participants'].values() if person['name']]
        if kind == 'close':
            for i, name in enumerate(names):
                text(draw, (132 + (i%2)*630, 655+(i//2)*63), name, config, 33, ivory)
    else:
        text(draw, (132, 291), item.get('kicker','CONVERSACIÓN LITERARIA'), config, 39, rust, bold=True)
        title = item.get('title', 'Detrás de cámaras')
        if len(title) > 22:
            words = title.split()
            cut = min(range(1,len(words)), key=lambda k: abs(len(' '.join(words[:k]))-len(' '.join(words[k:]))))
            title = ' '.join(words[:cut])+'\n'+' '.join(words[cut:])
        text(draw, (119, 377), title, config, 89, coal, serif=True, spacing=9)
    return image


def label(config, title, role=''):
    family = config['fonts']['sans']
    width = round(max(font(family,41,True).getlength(title),font(family,30).getlength(role))) + 61
    height = 140 if role else 92
    image = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(image)
    box = (0, 8, width-1, height-9)
    pale = config['palette']['ivory']
    draw.rectangle(box, fill=(*hex_rgb(config['palette']['coal']), 235))
    draw.rectangle((0, 8, 9, height-9), fill=config['palette']['rust'])
    text(draw, (28, 18 if role else 22), title, config, 41, pale, bold=True)
    if role:
        text(draw, (30, 76), role, config, 30, pale)
    return image


def score(path, duration, kind, rate):
    """Original four-note motif. FM, low chords and a filtered noise transient."""
    t = np.arange(round(rate*duration))/rate
    left = np.zeros_like(t)
    right = np.zeros_like(t)
    notes = (146.83, 174.61, 220., 196.)
    spacing = duration * .145
    for i, freq in enumerate(notes):
        age = np.maximum(t-(.12+i*spacing), 0)
        envelope = (1-np.exp(-age/.055))*np.exp(-age/(.65 if kind=='open' else .38))
        stereo = np.sin(2*np.pi*freq*age + .15*np.sin(2*np.pi*freq*2*age))
        voice = envelope*(stereo + .23*np.sin(4*np.pi*freq*age))
        left += voice*(.108+i*.012)
        right += voice*(.145-i*.012)
    pad = .041*(np.sin(2*np.pi*73.415*t)+.55*np.sin(2*np.pi*110*t))
    noise = np.random.default_rng(91).normal(0,1,len(t))
    air = np.convolve(noise,np.ones(42)/42,mode='same')*.08
    fade = np.sin(np.pi/2*np.minimum(t/.20,1)) * np.clip((duration-t)/.7,0,1)
    data = np.stack((left+pad+air,right+pad-air),axis=1)*fade[:,None]
    with wave.open(str(path), 'wb') as out:
        out.setparams((2,2,rate,0,'NONE','not compressed'))
        out.writeframes(np.int16(np.clip(data,-1,1)*32767).tobytes())
