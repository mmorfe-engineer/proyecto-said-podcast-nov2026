"""Versioned local production entry point. The V01 render paths remain intact."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import shutil

import render

ROOT = render.ROOT
WORK = ROOT/'work/v02'
OUT = ROOT/'renders/v02'
SUB = ROOT/'subtitles'
NAME = 'EL_TUNEL_V02'
BASE = json.loads((ROOT/'config/episodio.json').read_text())
EDIT = json.loads((ROOT/'config/v02.json').read_text())


def configure():
    identity = json.loads((ROOT/'config/identidad.local.json').read_text())
    render.CONFIG = {**BASE, **EDIT, **identity, 'edition': 'Una conversación literaria · 2026',
                     'audio': {**BASE['audio'], 'peak': -1.7}}
    render.WORK = WORK
    render.OUT = OUT
    render.NAME = NAME
    # The dual source render benefits from a quicker compression preset at archival quality.
    render.VIDEO = [v if v != 'veryfast' else 'superfast' for v in render.VIDEO]
    for folder in (WORK, OUT, SUB):
        folder.mkdir(parents=True, exist_ok=True)
    return render.prepare_timeline()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['dialogue','preview','clean','subtitled','audit'])
    stage = parser.parse_args().stage
    total = configure()
    rows = render.CONFIG['timeline']
    if stage == 'dialogue':
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(render.segment,(r for r in rows if 'card' not in r)))
        return
    if stage == 'audit':
        from v02_audit import audit
        audit(rows,total)
        return
    if stage == 'subtitled':
        from v02_subtitles import build
        build(rows)
        temp = WORK/'subtitled.mp4'
        render.ff('-v','error','-threads',3,'-i',OUT/f'{NAME}_LIMPIO.mp4','-vf',
                  "subtitles=subtitles/EL_TUNEL_V02.srt:force_style='FontName=Lato,FontSize=17,Bold=1,Outline=2,Shadow=0,MarginV=25,MarginL=45,MarginR=45'",
                  *render.VIDEO,'-c:a','copy','-movflags','+faststart',temp)
        temp.replace(OUT/f'{NAME}.mp4')
        return
    from v02_motion import motion
    if stage == 'preview':
        for row in rows:
            if 'card' in row:
                path = motion(row,rows)
                render.ff('-v','error','-i',path,'-c:v','copy','-c:a','aac','-movflags','+faststart',
                          OUT/'cortinas'/f'{row["id"]}.mp4')
        shutil.copyfile(OUT/'recursos/apertura/thumbnail.jpg',OUT/'thumbnail.jpg')
        return
    segments = [motion(row,rows) if 'card' in row else render.segment(row) for row in rows]
    from v02_assembly import assemble
    assemble(segments,rows,total)


if __name__ == '__main__':
    (OUT/'cortinas').mkdir(parents=True,exist_ok=True)
    try:
        main()
    except Exception as error:
        if getattr(error,'stderr',None):
            print(error.stderr.decode(errors='replace'))
        raise
