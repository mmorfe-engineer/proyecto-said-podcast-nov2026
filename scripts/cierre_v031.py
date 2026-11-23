"""Conformado final de V03.1 a partir de los dos másteres aprobados."""
import hashlib
import json
import re
import subprocess
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
from subtitles import seconds

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT/'renders/v03_1'
OUT = REF/'definitivo'
WORK = ROOT/'work/cierre-v031'
NAME = 'EL_TUNEL_V03_1'
EDIT = json.loads((ROOT/'config/cierre-v031.json').read_text())
LOGO = ROOT/EDIT['logo']
FPS = 30


def ff(*args):
    subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-filter_threads','2',
                    '-filter_complex_threads','2',*map(str,args)],check=True)


def keyframes(path):
    raw = subprocess.check_output(['ffprobe','-v','error','-select_streams','v','-show_entries',
        'packet=pts_time,flags','-of','json',str(path)])
    return sorted(round(float(p['pts_time'])*FPS) for p in json.loads(raw)['packets'] if 'K' in p['flags'])


def video(path, opening, cut, end, total):
    keys = keyframes(path)
    first = next(k for k in keys if k >= opening)
    last = max(k for k in keys if k <= cut)
    folder = WORK/path.stem
    folder.mkdir(exist_ok=True)
    parts = []
    def piece(start, stop, copy=False, mark=False):
        if stop == start:
            return
        dst = folder/f'{start}.mp4'
        args = ['-ss',f'{start/FPS:.9f}','-i',path]
        padded = mark and path.stem.endswith('_LIMPIO')
        # A distinct coded height forces H.264 decoders to reinitialize between
        # transform-bypass patches and the approved high-profile B-frame GOPs.
        # SPS cropping removes all 24 padding lines from the display aperture.
        padding = ',pad=1920:1104:0:0' if padded else ''
        if mark:
            args += ['-i',WORK/'escudo.png','-filter_complex',
                     f"[0:v][1:v]overlay=x=1664:y=80:enable='lt(n,{opening if start==0 else stop-start})'{padding}[v]",
                     '-map','[v]']
        else:
            args += ['-map','0:v']
        args += ['-an','-frames:v',stop-start]
        if copy:
            args += ['-c:v','copy']
        else:
            # Lossless patches preserve decoded pixels outside the crest, including
            # the short GOP handles needed by the burned-caption reference.
            args += ['-c:v','libx264','-preset','veryfast','-qp','0','-threads','4',
                     '-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709']
        if padded:
            args += ['-x264-params','crop-rect=0,0,0,24']
        ff(*args,'-video_track_timescale',30000,dst)
        parts.append((dst,stop-start))
    piece(0,first,mark=True)
    piece(first,last,copy=True)
    piece(last,cut)
    piece(end,total,mark=True)
    playlist=folder/'lista.txt'
    playlist.write_text(''.join(f"file '{p}'\nduration {n/FPS:.9f}\n" for p,n in parts))
    dst=OUT/path.name
    ff('-f','concat','-safe',0,'-i',playlist,'-i',WORK/'audio.m4a','-map','0:v','-map','1:a',
       '-c','copy','-video_track_timescale',30000,'-movflags','+faststart',dst)
    if path.stem.endswith('_LIMPIO'):
        # The copied B-frame stream and lossless patches use different decoder
        # delays. Regularize DTS without changing a single picture or its PTS.
        fixed=folder/'cfr.mp4'
        ff('-i',dst,'-map',0,'-c','copy','-bsf:v','setts=dts=(N-2)*1000:pts=PTS:duration=1000',
           '-video_track_timescale',30000,'-movflags','faststart',fixed)
        fixed.replace(dst)
    return dst


def conform():
    OUT.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    old=json.loads((REF/'edl.json').read_text())
    assert [old[0]['id'],old[-1]['id']]==EDIT['logo_cards']
    assert old[-3]['id']=='extra-coro' and old[-2]['id']==EDIT['remove']
    removed=old[-2]
    assert removed['blooper']=='c' and removed['frames']==312
    assert f"bloopers_{removed['blooper']}.mp4"==EDIT['source']
    assert hashlib.sha256(LOGO.read_bytes()).hexdigest()==EDIT['logo_sha256']
    cut,end=removed['start_frame'],old[-1]['start_frame']
    rows=old[:-2]+[{**old[-1],'start_frame':cut}]
    total=end+old[-1]['frames']
    (OUT/'edl.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    cues=(REF/f'{NAME}.srt').read_text().strip().split('\n\n')
    kept=[]
    for cue in cues:
        a,b=map(seconds,cue.splitlines()[1].split(' --> '))
        if b <= cut/FPS+.001:
            kept.append(cue)
        else:
            assert cut/FPS-.001<=a<b<=end/FPS+.001
    assert len(kept)==140 and len(cues)==143
    (OUT/f'{NAME}.srt').write_text('\n\n'.join(kept)+'\n')
    with Image.open(LOGO) as logo:
        assert logo.mode=='RGBA' and logo.size==(2000,2000)
        logo.resize((176,176),Image.Resampling.LANCZOS).save(WORK/'escudo.png')
    with wave.open(str(ROOT/'work/v03_1/mix.wav'),'rb') as src, wave.open(str(WORK/'corte.wav'),'wb') as dst:
        dst.setparams(src.getparams())
        dst.writeframesraw(src.readframes(cut*1600))
        src.setpos(end*1600)
        dst.writeframesraw(src.readframes((total-end)*1600))
        assert dst.tell()==(total-removed['frames'])*1600
    ff('-i',WORK/'corte.wav','-c:a','aac','-b:a','224k',WORK/'audio.m4a')
    files=[REF/f'{NAME}{suffix}.mp4' for suffix in ('_LIMPIO','')]
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda p:video(p,old[0]['frames'],cut,end,total),files))


if __name__=='__main__':
    conform()
