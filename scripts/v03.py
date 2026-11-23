"""Conform V03 against verified, locally retained V02 delivery material."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw

import audit
import render
from subtitles import seconds, srt_stamp
from v02_motion import layout as v02_layout
from v02_subtitles import PROHIBITED
from v03_motion import layout, logo_asset, motion

ROOT = render.ROOT
V02 = ROOT/'work/v02'
WORK = ROOT/'work/v03'
OUT = ROOT/'renders/v03'
MASTER = ROOT/'renders/v02/EL_TUNEL_V02_LIMPIO.mp4'
NAME = 'EL_TUNEL_V03'
FPS = 30
RATE = 48000
SAMPLES = RATE//FPS
EDIT = json.loads((ROOT/'config/v03.json').read_text())


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def verified_inputs():
    """Match the approved source rows and the retained V02 conform manifest."""
    rows = json.loads((V02/'edl.json').read_text())
    tracked = json.loads((ROOT/'config/v02.json').read_text())['timeline']
    assert [{k: v for k, v in row.items() if k not in ('start_frame', 'frames')} for row in rows] == tracked
    files = re.findall(r"(?m)^file '([^']+)'$", (V02/'concat.txt').read_text())
    segments = {row['id']: V02/file for row, file in zip(rows, files, strict=True)}
    for row in rows:
        path = segments[row['id']]
        assert path.is_file() and (
            path.stem == row['id'] if 'card' in row else path.parent.name.startswith(row['id']+'-')), path
    return rows, segments


def conform(source):
    replacement = EDIT['cards']
    inserts = EDIT['inserts']
    removed = [row for row in source if 'blooper' in row][-1]
    assert (removed['id'], removed['blooper'], removed['in'], removed['out']) == (EDIT['remove'], 5, 10.15, 23.65)
    rows = []
    for row in source:
        if row == removed:
            continue
        rows.append({**row, **replacement.get(row['id'], {})})
        rows.extend(dict(insert) for insert in inserts.get(row['id'], []))
    cursor = 0
    for row in rows:
        row['start_frame'] = cursor
        if 'card' in row:
            row['frames'] = round(row['duration']*FPS)
            if row['card'] == 'chapter':
                assert len(row['deck'].split()) <= 20
        cursor += row['frames']
    verification(source, rows)
    return rows, cursor


def verification(source, rows):
    def frozen(items, kind):
        return [{**{k: v for k, v in r.items() if k != 'start_frame'},
                 'source': str(render.source(r).relative_to(ROOT))}
                for r in items if kind in r]

    before = frozen(source, 'clip')
    after = frozen(rows, 'clip')
    assert before == after
    assert {row['clip'] for row in after} == set(range(1, 9))
    assert frozen(source, 'blooper')[:-1] == frozen(rows, 'blooper')
    tracked_before = {row['id']: row['start_frame'] for row in source}
    tracked_after = {row['id']: row['start_frame'] for row in rows}
    return {'dialogue_identical': True, 'sources': 8, 'dialogue_segments': 9,
            'windows': [{**row, 'v02_start_frame': tracked_before[row['id']],
                         'v03_start_frame': tracked_after[row['id']]} for row in after],
            'bloopers_kept': frozen(rows, 'blooper'), 'blooper_removed': EDIT['remove']}


def captions(before, rows):
    approved = (ROOT/'subtitles/EL_TUNEL_V02.srt').read_text()
    current = {row['id']: row for row in rows}
    result = []
    prior = 0
    for block in approved.strip().split('\n\n'):
        index, bounds, *lines = block.splitlines()
        a, b = map(seconds, bounds.split(' --> '))
        row = next(row for row in before if row['start_frame']/FPS-.001 <= a <
                   (row['start_frame']+row['frames'])/FPS)
        assert 'card' not in row and b <= (row['start_frame']+row['frames'])/FPS+.001, index
        if row['id'] not in current:
            assert row['id'] == EDIT['remove']
            continue
        change = (current[row['id']]['start_frame']-row['start_frame'])/FPS
        a, b = a+change, b+change
        assert a >= prior-.00001 and b > a and 1 <= len(lines) <= 2 and max(map(len, lines)) <= 41
        assert not PROHIBITED.search(' '.join(lines)) and '[' not in ''.join(lines)
        result.append('\n'.join([str(len(result)+1), f'{srt_stamp(a)} --> {srt_stamp(b)}', *lines]))
        prior = b
    (OUT/f'{NAME}.srt').write_text('\n\n'.join(result)+'\n')
    return len(result)


def repair(samples, row):
    """Reduce the high-frequency component only around the marked transients."""
    settings = EDIT['audio_repair']
    report = []
    for start, end in settings['v02_windows']:
        origin = row['start_frame']/FPS
        a, b = round((start-origin)*RATE), round((end-origin)*RATE)
        assert 0 < a < b < len(samples)
        target = samples[a:b].astype(float)
        width = min(round(.016*RATE), len(target)//3)
        taper = np.ones(len(target))
        taper[:width] = np.sin(np.linspace(0, np.pi/2, width))**2
        taper[-width:] = taper[:width][::-1]
        padding = 512
        context = np.pad(target, ((padding, padding), (0, 0)), mode='reflect')
        frequencies = np.fft.rfftfreq(len(context), 1/RATE)
        weight = np.clip((frequencies-2450)/1800, 0, 1)
        high = np.fft.irfft(np.fft.rfft(context, axis=0)*weight[:, None],
                            n=len(context), axis=0)[padding:-padding]
        gain = 10**(settings['high_band_gain_db']/20)
        corrected = np.rint(target - high*taper[:, None]*(1-gain))
        samples[a:b] = np.clip(corrected, -32768, 32767).astype('<i2')
        report.append({'v02': [start, end], 'source': [round(row['in']+start-origin, 4),
                                                       round(row['in']+end-origin, 4)],
                       'changed_samples_per_channel': b-a,
                       'difference_rms': round(float(np.sqrt(np.mean((corrected-target)**2))), 2)})
    return report


def audio(paths, before, rows, total):
    raw = WORK/'referencia/v02-pcm.wav'
    render.ff('-v', 'error', '-i', MASTER, '-map', '0:a:0', '-c:a', 'pcm_s16le', raw)
    references = {row['id']: row for row in before}
    report = []
    with wave.open(str(raw), 'rb') as reference, wave.open(str(WORK/'mezcla.wav'), 'wb') as output:
        assert reference.getframerate() == RATE and reference.getnchannels() == 2
        output.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        for path, row in zip(paths, rows, strict=True):
            count = row['frames']*SAMPLES
            old = references.get(row['id'])
            if old is not None and row['id'] not in EDIT['cards']:
                reference.setpos(old['start_frame']*SAMPLES)
                data = reference.readframes(count)
                if row['id'] == EDIT['audio_repair']['id']:
                    samples = np.frombuffer(data, '<i2').reshape(-1, 2).copy()
                    report = repair(samples, old)
                    original = np.frombuffer(data, '<i2').reshape(-1, 2)
                    protected = np.ones(len(samples), dtype=bool)
                    for start, end in EDIT['audio_repair']['v02_windows']:
                        a, b = [round((t-old['start_frame']/FPS)*RATE) for t in (start, end)]
                        protected[a:b] = False
                    assert np.array_equal(original[protected], samples[protected])
                    data = samples.tobytes()
            else:
                data = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
                                                '-map', '0:a:0', '-f', 's16le', '-'])
            assert len(data) == count*4, row['id']
            output.writeframesraw(data)
        assert output.tell() == total*SAMPLES
    write_json(WORK/'audio.json', report)


def card_paths(rows, old_paths, logo_path, logo):
    paths = []
    for row in rows:
        name = row['id']
        if 'card' not in row or row['card'] == 'bloopers':
            path = old_paths[name]
        else:
            path = motion(row, logo_path, logo)
        if 'card' in row:
            target = OUT/'cortinas'/f'{name}.mp4'
            if not target.exists() or target.stat().st_mtime_ns < path.stat().st_mtime_ns:
                render.ff('-v', 'error', '-i', path, '-c:v', 'copy', '-c:a', 'aac',
                          '-movflags', '+faststart', target)
        paths.append(path)
    return paths


def assemble(paths, rows, total):
    playlist = WORK/'concat.txt'
    playlist.write_text(''.join(f"file '{path}'\n"
                                f"duration {row['frames']/FPS:.9f}\n"
                                for path, row in zip(paths, rows, strict=True)))
    clean = OUT/f'{NAME}_LIMPIO.mp4'
    render.ff('-v', 'error', '-f', 'concat', '-safe', 0, '-i', playlist, '-i', WORK/'mezcla.wav',
              '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '224k',
              '-t', f'{total/FPS:.9f}', '-video_track_timescale', 30000, '-movflags', '+faststart',
              WORK/'limpio.part.mp4')
    (WORK/'limpio.part.mp4').replace(clean)
    subtitled()


def subtitled():
    clean = OUT/f'{NAME}_LIMPIO.mp4'
    srt = f'renders/v03/{NAME}.srt'
    style = 'FontName=Lato,FontSize=17,Bold=1,Outline=2,Shadow=0,MarginV=25,MarginL=45,MarginR=45'
    temp = WORK/'subtitulado.part.mp4'
    codec = ['ultrafast' if value == 'superfast' else value for value in render.VIDEO]
    codec[codec.index('-threads')+1] = '8'
    subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-threads', '6',
                    '-i', str(clean), '-filter_threads', '3',
                    '-vf', f"subtitles={srt}:force_style='{style}'", *codec,
                    '-c:a', 'copy', '-video_track_timescale', '30000', '-movflags',
                    '+faststart', str(temp)], cwd=ROOT, check=True)
    temp.replace(OUT/f'{NAME}.mp4')


def frame_hashes(path):
    """Hash decoded video frames independently of packet representation."""
    cmd = ['ffmpeg', '-v', 'error', '-threads', '4', '-i', str(path), '-map', '0:v:0',
           '-an', '-c:v', 'rawvideo', '-threads:v', '1', '-f', 'framemd5', '-']
    lines = subprocess.check_output(cmd, text=True).splitlines()
    return [line.rsplit(',', 1)[-1].strip() for line in lines if line and not line.startswith('#')]


def audit_delivery(before, rows, total, count):
    audit.WORK = WORK
    files = [OUT/f'{NAME}_LIMPIO.mp4', OUT/f'{NAME}.mp4']
    with ThreadPoolExecutor(max_workers=3) as pool:
        contact = pool.submit(audit.contact, files[1], rows)
        deliveries = list(pool.map(lambda path: audit.validate(path, total), files))
        contact.result()
    shutil.copyfile(WORK/'qa/hoja-contacto.jpg', OUT/'hoja-contacto.jpg')
    with ThreadPoolExecutor(max_workers=2) as pool:
        previous, final = pool.map(frame_hashes, (MASTER, files[0]))
    original = {row['id']: row for row in before}
    compared = {}
    for row in rows:
        if 'card' in row:
            continue
        a = original[row['id']]['start_frame']
        b = row['start_frame']
        duration = row['frames']
        assert previous[a:a+duration] == final[b:b+duration], row['id']
        compared[row['id']] = duration
    hashes = [audit.run('ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a',
                        '-c', 'copy', '-f', 'hash', '-hash', 'sha256', '-')[0].strip() for path in files]
    assert hashes[0] == hashes[1]
    for path, data in zip(files, deliveries, strict=True):
        data['file'] = path.name
    assert len(previous) == sum(row['frames'] for row in before)
    assert len(final) == total
    preservation = audit.run('sha256sum', '-c', str(V02/'preservacion.sha256'))[0]
    return {'preserved_files': len(preservation.splitlines()), 'deliveries': deliveries, 'captions': count, 'audio_packet_hash': hashes[0],
            'identical_decoded_frames': compared}


def public_gallery(rows):
    gallery = ROOT/'docs/galeria-v03'
    gallery.mkdir(exist_ok=True)
    for row in rows:
        image = (v02_layout(row, 4.2) if row['card'] == 'bloopers'
                 else layout(row, 4.2, public=True))
        image.save(gallery/f'{row["id"]}.jpg', quality=90)
        if row['card'] == 'open':
            image.resize((1280, 720), Image.Resampling.LANCZOS).save(gallery/'miniatura.jpg', quality=92)
    sheet = Image.new('RGB', (1200, 690), '#15171b')
    draw = ImageDraw.Draw(sheet)
    chapter = next(row for row in rows if row['id'] == 'capitulo-3')
    for index, t in enumerate((.8, 1.6, 2.3, 4)):
        x, y = index%2*600, index//2*345
        sheet.paste(layout(chapter, t, public=True).resize((600, 337)), (x, y))
        draw.line((x, y+337, x+600, y+337), fill='#a77969', width=2)
    sheet.save(gallery/'motion.jpg', quality=91)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('edl', 'preview', 'build', 'subtitled', 'audit', 'gallery'))
    stage = parser.parse_args().stage
    for path in (WORK/'referencia', OUT/'cortinas'):
        path.mkdir(parents=True, exist_ok=True)
    identity = ROOT/'config/identidad-v03.local.json'
    if stage not in ('edl', 'gallery') and not identity.exists():
        parser.error(f'Falta {identity.relative_to(ROOT)}')
    render.CONFIG.update(json.loads((identity if identity.exists() else
                        ROOT/'config/identidad-v03.example.json').read_text()))
    render.WORK, render.OUT = WORK, OUT
    render.VIDEO = ['superfast' if value == 'veryfast' else value for value in render.VIDEO]
    before, old_paths = verified_inputs()
    write_json(WORK/'edl-v02-referencia.json', before)
    rows, total = conform(before)
    write_json(OUT/'edl.json', rows)
    write_json(OUT/'conservacion-edl.json', verification(before, rows))
    if stage == 'edl':
        return
    if stage == 'gallery':
        public_gallery([row for row in rows if 'card' in row])
        return
    count = captions(before, rows)
    if stage == 'subtitled':
        subtitled()
        return
    if stage == 'audit':
        results = audit_delivery(before, rows, total, count)
        write_json(OUT/'auditoria.json', results)
        print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)
        return
    logo_path, logo = logo_asset(ROOT/'logo colegio')
    write_json(WORK/'logo.json', {'source': str(logo_path.relative_to(ROOT)) if logo_path else None,
                                'sha256': hashlib.sha256(logo_path.read_bytes()).hexdigest() if logo_path else None})
    if stage == 'preview':
        selection = [row for row in rows if row['id'] in ('apertura', 'capitulo-3', 'mapa', 'agradecimiento')]
        card_paths(selection, old_paths, logo_path, logo)
        return
    paths = card_paths(rows, old_paths, logo_path, logo)
    audio(paths, before, rows, total)
    assemble(paths, rows, total)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        if error.stderr:
            print(error.stderr.decode(errors='replace') if isinstance(error.stderr, bytes) else error.stderr)
        raise
