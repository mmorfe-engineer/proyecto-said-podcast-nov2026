"""Export a lightweight review file and locally generated artwork."""
import argparse
import shutil

from render import CONFIG, NAME, OUT, WORK, ff, prepare, prepare_timeline
from graphics import card


def assets():
    prepare_timeline()
    art = OUT/'recursos'
    for item in CONFIG['timeline']:
        if not any(key in item for key in ('card','labels','cover','callout')):
            continue
        folder = art/item['id']
        folder.mkdir(parents=True,exist_ok=True)
        prepare(item,folder)
        for still in folder.glob('*source.jpg'):
            still.unlink()
        portrait = folder/'portrait.jpg'
        if portrait.exists():
            portrait.unlink()
    shutil.copyfile(WORK/'edl.json',art/'edl.json')
    card(CONFIG,CONFIG['timeline'][0]).resize((1280,720)).save(OUT/'thumbnail.jpg',quality=94)


def review():
    ff('-v','error','-threads',3,'-i',OUT/f'{NAME}_SUBTITULADO.mp4',
       '-vf','scale=1280:720:flags=lanczos','-c:v','libx264','-preset','ultrafast','-crf',22,
       '-threads',4,'-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',
       OUT/f'{NAME}_REVISION.mp4')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['all','assets','review'],nargs='?',default='all')
    mode = parser.parse_args().mode
    if mode in ('all','assets'):
        assets()
    if mode in ('all','review'):
        review()
