"""Charcoal artwork for the institutional and pedagogical V03 cards."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave

import numpy as np

from PIL import Image, ImageDraw, ImageOps

from graphics import font

import render
from v02_motion import W, H, draw_text, ease, grain, music, still, strokes, wipe, wrap

INK = (216, 138, 114)


def logo_asset(folder):
    """Return an unmodified source and a proportional raster preview."""
    candidates = []
    for path in sorted(folder.rglob('*')):
        if not path.is_file():
            continue
        try:
            if path.suffix.lower() == '.svg':
                import cairosvg
                from io import BytesIO

                source = BytesIO(cairosvg.svg2png(url=str(path), output_width=384))
            else:
                source = path
            with Image.open(source) as image:
                mark = image.convert('RGBA')
            if mark.getbbox() and min(mark.size) >= 40:
                candidates.append((path, mark))
        except (OSError, ValueError, ImportError, SyntaxError):
            continue
    if not candidates:
        return None, None
    path, mark = max(candidates, key=lambda item: (item[0].suffix.lower() == '.svg', min(item[1].size)))
    return path, ImageOps.contain(mark, (90, 80), Image.Resampling.LANCZOS)


def text_block(draw, text, x, y, width, size, opacity):
    for line in wrap(text, size, width):
        draw_text(draw, x, y, line, size, opacity)
        y += size + 6
    return y


def people(draw, opacity, y):
    for index, person in enumerate(render.CONFIG['participants'].values()):
        name = person['name']
        draw_text(draw, 65 + index % 2 * 400, y + index // 2 * 51,
                  name, 27, opacity, serif=True)


def diagram(draw, t):
    points = [(179, 247), (470, 212), (755, 247), (300, 367), (644, 367)]
    labels = ['Celos patológicos', 'Necesidad de posesión', 'Cosificación', 'Control', 'Aislamiento']
    for index, (a, b) in enumerate([(0, 1), (1, 2), (0, 3), (1, 3), (2, 4), (3, 4)]):
        x, y = points[a]
        xx, yy = points[b]
        progress = ease(t, .75 + index * .19, 2.55 + index * .19)
        draw.line((x, y, x + (xx-x)*progress, y + (yy-y)*progress), fill=INK, width=2)
    for index, ((x, y), label) in enumerate(zip(points, labels, strict=True)):
        progress = ease(t, .65 + index * .22, 1.25 + index * .22)
        if progress:
            draw.rounded_rectangle((x-119, y-23, x+119, y+23), 5,
                                   fill='#232429', outline='#a77969', width=1)
            draw_text(draw, x, y, label, 19, progress, anchor='mm')


def layout(row, t, logo=None, public=False, thumbnail=False):
    kind = row['card']
    duration = row['frames']/30
    number = row.get('number', 0)
    image = grain().copy()
    reveal = ease(t, .08, 2.6)
    if kind == 'end':
        reveal *= 1 - .78 * ease(t, 5, duration - .7)
    strokes(image, number, t, reveal)
    shade = Image.new('RGB', (W, H), '#14161a')
    image = Image.blend(image, shade, .76 if kind in ('capsule', 'map') else .22)
    draw = ImageDraw.Draw(image)
    p = ease(t, .25, 1.22)
    q = ease(t, .7, 1.65)
    institution = render.CONFIG['institution']
    if logo is not None and not public:
        opacity = logo.getchannel('A').point(lambda v: round(v*p))
        image.paste(logo, (W-55-logo.width, 39), opacity)
    draw.line((64, 103, 64 + 55 * p, 103), fill=INK, width=2)
    if kind == 'open':
        institutional = institution.upper() if not public else 'VIDEOPODCAST LITERARIO'
        draw_text(draw, 64, 46, institutional, 21, p, tone=INK)
        draw_text(draw, 64, 74, 'LITERATURA · KLASSE 11 "A"  /  PRUEBA SEMESTRAL I' if not public
                  else 'VIOLENCIA DE GÉNERO EN LA LITERATURA', 15, p)
        if thumbnail or public or t < 8.1:
            opacity = q * (1 - ease(t, 7.35, 8.1)) if not (thumbnail or public) else q
            draw_text(draw, 59, 124, 'EL TÚNEL', 94, opacity, serif=True)
            draw_text(draw, 64, 243, 'Ernesto Sabato', 30, opacity, serif=True, tone=INK)
            draw_text(draw, 64, 302, 'Violencia de género en la obra', 28, opacity)
            draw_text(draw, 64, 346, 'Cuando el control se disfraza de amor', 24, opacity)
            draw_text(draw, 64, 453, 'Prueba semestral I · Actividad sustitutiva' if not public
                      else 'CHARCOAL MOTION EDITORIAL', 16, opacity, tone=INK)
        else:
            opacity = ease(t, 8.15, 9.2)
            draw_text(draw, 63, 145, 'EL TÚNEL', 62, opacity, serif=True)
            draw_text(draw, 65, 237, 'INTEGRANTES', 17, opacity, tone=INK)
            people(draw, opacity, 284)
    elif kind in ('close', 'end'):
        draw_text(draw, 64, 46, 'VIDEOPODCAST LITERARIO' if public else institution.upper(), 19, p, tone=INK)
        draw_text(draw, 60, 119, 'EL TÚNEL', 70, q, serif=True)
        draw_text(draw, 65, 210, 'Gracias por acompañarnos' if kind == 'end'
                  else 'Cuando el control se disfraza de amor', 30, q)
        if not public:
            people(draw, ease(t, 1.1, 2.15), 289)
            draw_text(draw, 65, 436, render.CONFIG['class'], 20, q, tone=INK)
        if kind == 'end':
            image = Image.blend(image, shade, .90 * ease(t, duration-1.5, duration-.03))
    else:
        if kind == 'chapter':
            section = f'CAPÍTULO {("I", "II", "III", "IV")[number-1]}'
        elif kind == 'bridge':
            section = 'REFLEXIÓN'
        else:
            section = 'LECTURA GUIADA'
        draw_text(draw, 64, 69, section, 18, p, tone=INK)
        if kind in ('capsule', 'map'):
            draw_text(draw, 61, 122, row['title'], 49, q, serif=True)
            if kind == 'map':
                diagram(draw, t)
            else:
                for index, (heading, wording) in enumerate(row['lines']):
                    y = 219 + 69 * index
                    opacity = ease(t, 1 + index * .38, 2 + index * .38)
                    draw_text(draw, 65, y, heading, 15, opacity, tone=INK)
                    text_block(draw, wording, 65, y+23, 810, 24, opacity)
            draw_text(draw, 65, 466, row['note'], 16, q)
        else:
            face = render.CONFIG['fonts']['serif']
            lines = ['']
            for word in row['title'].split():
                candidate = (lines[-1]+' '+word).strip()
                if lines[-1] and font(face, 57).getlength(candidate) > 565:
                    lines.append(word)
                else:
                    lines[-1] = candidate
            for index, line in enumerate(lines):
                draw_text(draw, 60, 154 + index * 66, line, 57, q, serif=True)
            text_block(draw, row['deck'], 65, 323, 475, 24, ease(t, 1.6, 2.4))
            if kind == 'chapter' and not public:
                draw_text(draw, 65, 475, institution, 16, p, tone=INK)
    return image


def score(path, row):
    music(path, row)
    if row['card'] != 'end':
        return
    with wave.open(str(path), 'rb') as source:
        params = source.getparams()
        samples = np.frombuffer(source.readframes(params.nframes), '<i2').reshape(-1, 2).astype(float)
    rate = params.framerate
    t = np.arange(len(samples))/rate
    duration = len(samples)/rate
    age = np.maximum(0, t-(duration-3.6))
    envelope = (1-np.exp(-age/.18))*np.exp(-age/.95)*np.clip((duration-t)/.6, 0, 1)
    for frequency in (146.83, 220, 293.66):
        for channel in range(2):
            samples[:, channel] += 1080*envelope*np.sin(math.tau*frequency*age+channel*.09)
    with wave.open(str(path), 'wb') as target:
        target.setparams(params)
        target.writeframes(np.rint(samples).clip(-32768,32767).astype('<i2').tobytes())


def motion(row, logo_path, logo):
    directory = render.OUT/'recursos'/row['id']
    directory.mkdir(parents=True, exist_ok=True)
    target = render.WORK/f'{row["id"]}.mov'
    stamp = directory/'render.sha256'
    sources = [Path(__file__), Path(__file__).with_name('v02_motion.py')]
    if logo_path is not None:
        sources.append(logo_path)
    refs = [reference for reference in (row.get('prev'), row.get('next')) if reference]
    sources.extend(render.source({'clip': reference[0]}) for reference in refs)
    if row.get('prev_blooper'):
        sources.append(render.source({'blooper': row['prev_blooper'][0]}))
    inputs = [row, {name: render.CONFIG[name] for name in ('participants', 'fonts', 'institution', 'class')}]
    key = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode())
    for path in sources:
        with path.open('rb') as stream:
            key.update(hashlib.file_digest(stream, 'sha256').digest())
    if target.exists() and stamp.exists() and stamp.read_text() == key.hexdigest():
        return target
    previous = still(row.get('prev'), directory/'prev.jpg')
    following = still(row.get('next'), directory/'next.jpg')
    if row.get('prev_blooper'):
        source, at = row['prev_blooper']
        render.ff('-v', 'error', '-ss', at, '-i', render.source({'blooper': source}),
                  '-frames:v', 1, '-vf', 'scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2',
                  '-threads', 1, directory/'prev.jpg')
        with Image.open(directory/'prev.jpg') as frame:
            previous = frame.convert('RGB')
    score(directory/'motivo.wav', row)
    for idx, t in enumerate((.85, 2.8, row['frames']/60, row['frames']/30 - .85)):
        layout(row, t, logo).save(directory/f'muestra-{idx+1}.jpg', quality=93)
    if row['card'] == 'open':
        layout(row, 4, logo, thumbnail=True).resize((1280,720), Image.Resampling.LANCZOS).save(
            render.OUT/'thumbnail.jpg', quality=94)
    command = ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
               '-video_size', f'{W}x{H}', '-framerate', '30', '-i', 'pipe:0',
               '-i', str(directory/'motivo.wav'), '-filter_threads', '2',
               '-vf', 'scale=1920:1080:flags=lanczos:out_range=limited,format=yuv420p,setsar=1',
               *render.VIDEO, '-ar', '48000', '-c:a', 'pcm_s16le', '-video_track_timescale', '30000']
    temp = target.with_suffix('.part.mov')
    with subprocess.Popen([*command, str(temp)], stdin=subprocess.PIPE) as encoder:
        for frame in range(row['frames']):
            t = frame/30
            art = layout(row, t, logo)
            if previous is not None and t < .53:
                art = wipe(previous, art, t/.53)
            remainder = (row['frames']-frame-1)/30
            if following is not None and remainder < .53:
                art = wipe(following, art, remainder/.53)
            encoder.stdin.write(art.tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError(f'Falló {row["id"]}')
    temp.replace(target)
    stamp.write_text(key.hexdigest())
    print(f'Cortina {row["id"]}: {row["frames"]} fotogramas', flush=True)
    return target
