"""El túnel V03.1. Run prepare, review, build, then audit from the project root."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import re
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw
import audit
import render
import v03
from v031_reports import reports
from v02_motion import layout as old_layout
from v03_motion import layout, logo_asset

ROOT = render.ROOT
OLD = ROOT/'renders/v03'
OUT = ROOT/'renders/v03_1'
WORK = ROOT/'work/v03_1'
NAME = 'EL_TUNEL_V03_1'
REFERENCE = OLD/'EL_TUNEL_V03_LIMPIO.mp4'
RATE = 48000


def ff(*args):
    subprocess.run(['ffmpeg','-hide_banner','-nostdin','-v','error','-y','-filter_threads','2',
                    '-filter_complex_threads','2',*map(str,args)], check=True)


def timeline():
    old = json.loads((OLD/'edl.json').read_text())
    rows = []
    cursor = 0
    for source in old:
        row = {k:v for k,v in source.items() if k not in ('prev','next','prev_blooper')}
        row['start_frame'] = cursor
        if row['id'] == 'extra-cierre':
            end = float(audit.probe(render.source(row))['streams'][0]['duration'])
            row['frames'] = math.floor((end-row['in'])*30+.0001)
            row['out'] = row['in']+row['frames']/30
        cursor += row['frames']
        rows.append(row)
    return rows


def loud(path, start=0, duration=None):
    cmd = ['ffmpeg','-hide_banner','-nostdin','-ss',str(start)]
    if duration is not None:
        cmd += ['-t',str(duration)]
    cmd += ['-i',str(path),'-vn','-af','loudnorm=print_format=json','-f','null','-']
    stats = json.loads(re.findall(r'\{[^{}]+\}',subprocess.run(cmd,check=True,capture_output=True,text=True).stderr)[-1])
    return float(stats['input_i'])


def signature(row, path):
    """D–A–F–E motif with damped hammer partials and a soft stereo celesta."""
    kind = row['card']
    duration = row['frames']/30
    t = np.arange(row['frames']*1600)/RATE
    notes = [62,69,65,64]
    starts = [.16,1.8,3.7,6.1]
    goal = -21
    if kind == 'chapter':
        step = row['number']-1
        notes = [62, [65,69,67,65][step], [64,62,65,62][step]]
        starts = [.14,1.15+step*.09,3.35]
        goal = -22
    elif kind in ('capsule','map'):
        starts = [.15,2.1,duration*.5,duration-2.3]
        goal = -25
    elif kind == 'bloopers':
        notes, starts, goal = [62,69,66,69],[.13,.65,1.15,2.25],-22
    elif kind == 'end':
        notes, starts = [62,69,65,64,62],[.16,1.8,3.7,duration-4.1,duration-2.6]
    elif kind == 'bridge':
        notes, starts, goal = [62,65,64],[.2,2.2,4.6],-25
    signal = np.zeros((len(t),2))
    for i,(midi,onset) in enumerate(zip(notes,starts,strict=True)):
        age = np.maximum(0,t-onset)
        f = 440*2**((midi-69)/12)
        for ch in (0,1):
            phase = 2*np.pi*f*age*(1+(ch-.5)*.0005)
            body = (np.sin(phase)+.29*np.sin(2*phase)+.10*np.sin(3*phase))*np.exp(-age/1.05)
            bell = .32*np.sin(phase*4.01)*np.exp(-age/.48)
            signal[:,ch] += (1-np.exp(-age/.017))*(body+bell)*(1-.08*((i+ch)%2))
    signal *= np.clip((duration-t)/.48,0,1)[:,None]
    def save(scale):
        with wave.open(str(path),'wb') as file:
            file.setparams((2,2,RATE,0,'NONE','not compressed'))
            file.writeframes(np.rint(signal*scale*32767).astype('<i2').tobytes())
    peak = np.max(abs(signal))
    save(.5/peak)
    gain = min(.66/peak,.5/peak*10**((goal-loud(path))/20))
    save(gain)


def card(row, logo):
    name = row['id']
    wav = OUT/'musica'/f'{name}.wav'
    signature(row,wav)
    target = WORK/f'{name}.mov'
    duration = row['frames']/30
    # Enter the animated artwork at reading opacity. Keep a live drawing clock.
    def art(t):
        if row['card'] == 'bloopers':
            return old_layout(row,3.2+t*.48,portrait)
        if row['card'] == 'open':
            clock = 2.7+t*.50 if t<8.2 else 9.25+(t-8.2)*.83
        else:
            clock = 2.6+t*(duration-2.6)/duration
        return layout(row,clock,logo)
    portrait = None
    if row['card']=='bloopers':
        from graphics import charcoal
        with Image.open(ROOT/'work/v02/detras-de-camaras-portrait.jpg') as img:
            portrait = charcoal(img.convert('RGB'),render.CONFIG).resize((357,259),Image.Resampling.LANCZOS)
    cmd = ['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','960x540',
           '-r','30','-i','-','-i',str(wav),'-filter_threads','2','-vf',
           'scale=1920:1080:flags=lanczos:out_range=limited,format=yuv420p,setsar=1',
           *render.VIDEO,'-video_track_timescale','30000','-c:a','pcm_s16le',str(target)]
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as proc:
        for i in range(row['frames']):
            proc.stdin.write(art(i/30).tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError(name)
    print(name,flush=True)
    return target


def prepare(rows):
    _, media = v03.verified_inputs()
    logo_path, logo = logo_asset(ROOT/'logo colegio')
    pieces = []
    with wave.open(str(ROOT/'work/v03/mezcla.wav'),'rb') as ref, wave.open(str(WORK/'mix.wav'),'wb') as mix:
        mix.setparams(ref.getparams())
        for row in rows:
            name = row['id']
            if 'card' in row:
                piece = card(row,logo)
                with wave.open(str(OUT/'musica'/f'{name}.wav'),'rb') as w:
                    data = w.readframes(row['frames']*1600)
            elif name == 'extra-cierre':
                piece = render.segment(row)
                data = subprocess.check_output(['ffmpeg','-v','error','-i',str(piece),'-vn','-f','s16le','-'])
            else:
                piece = media[name]
                ref.setpos(row['start_frame']*1600)
                data = ref.readframes(row['frames']*1600)
            assert len(data)==6400*row['frames'], name
            mix.writeframesraw(data)
            pieces.append(piece)
    (WORK/'lista.txt').write_text(''.join(f"file '{p}'\nduration {r['frames']/30:.9f}\n" for p,r in zip(pieces,rows,strict=True)))
    v03.write_json(OUT/'edl.json',rows)
    srt = (OLD/'EL_TUNEL_V03.srt').read_text().rstrip()
    (OUT/f'{NAME}.srt').write_text(srt+'\n\n143\n00:11:58,343 --> 00:12:01,800\nencerró en la mente…\n\n')
    v03.write_json(WORK/'identidad.json',{'logo':str(logo_path) if logo_path else None})


def review(rows):
    old = json.loads((OLD/'edl.json').read_text())
    paths = [Path(p) for p in re.findall(r"file '([^']+)'",(WORK/'lista.txt').read_text())]
    sheet = Image.new('RGB',(1120, (len(rows)-1)*105),'#16181a')
    draw = ImageDraw.Draw(sheet)
    reels = {'v03':[], 'v031':[]}
    def excerpt(i,offset,n,label):
        for version in reels:
            dst = WORK/f'{label}-{version}.mp4'
            if version=='v03':
                source = REFERENCE
                start = (old[i]['start_frame']+offset)/30
                if offset<0:
                    start = (old[i]['start_frame']+old[i]['frames']+offset)/30
                sound = source
            else:
                source = paths[i]
                absolute = rows[i]['start_frame']+(offset if offset>=0 else rows[i]['frames']+offset)
                start = (absolute-rows[i]['start_frame'])/30
                sound = WORK/'mix.wav'
            sound_start = start if version=='v03' else absolute/30
            ff('-ss',f'{start:.8f}','-i',source,'-ss',f'{sound_start:.8f}','-i',sound,
               '-map','0:v','-map','1:a','-t',f'{n/30:.8f}','-vf','scale=480:270',
               '-c:v','libx264','-threads','2','-preset','ultrafast','-c:a','pcm_s16le',
               '-f','mov',dst.with_suffix('.mov'))
            reels[version].append(dst.with_suffix('.mov'))
    excerpt(0,0,120,'inicio')
    for i in range(1,len(rows)):
        excerpt(i-1,-23,23,f'{i:02}-a')
        excerpt(i,0,23,f'{i:02}-b')
        for side,clip in enumerate(reels['v031'][-2:]):
            raw = subprocess.check_output(['ffmpeg','-v','error','-i',str(clip),'-vf','scale=175:80',
                                         '-threads','1','-f','rawvideo','-pix_fmt','rgb24','-'])
            frames = np.frombuffer(raw,np.uint8).reshape(-1,80,175,3)
            assert len(frames)==23
            for j,k in enumerate((0,11,22)):
                sheet.paste(Image.fromarray(frames[k]),((3*side+j)*182,(i-1)*105))
        draw.text((6,(i-1)*105+82),f"{rows[i]['start_frame']/30:.3f}s   {rows[i-1]['id']}  /  {rows[i]['id']}",fill='white')
    excerpt(len(rows)-1,-100,100,'final')
    sheet.save(OUT/'limites.jpg',quality=94)
    for key,clips in reels.items():
        playlist=WORK/f'reel-{key}.txt'
        playlist.write_text(''.join(f"file '{p}'\n" for p in clips))
        ff('-f','concat','-safe',0,'-i',playlist,'-c:v','copy','-c:a','aac',OUT/f'reel-{key}.mp4')
    ff('-i',OUT/'reel-v03.mp4','-i',OUT/'reel-v031.mp4','-filter_complex',
       '[0:v][1:v]hstack[v]','-map','[v]','-map','0:a','-map','1:a','-metadata:s:a:0',
       'title=V03','-metadata:s:a:1','title=V03.1','-threads','3','-c:a','copy',OUT/'comparativa.mp4')


def build(rows):
    total=sum(r['frames'] for r in rows)
    clean=OUT/f'{NAME}_LIMPIO.mp4'
    ff('-f','concat','-safe',0,'-i',WORK/'lista.txt','-i',WORK/'mix.wav','-map','0:v',
       '-map','1:a','-c:v','copy','-c:a','aac','-b:a','224k','-video_track_timescale',
       '30000','-t',f'{total/30:.8f}','-movflags','faststart',clean)
    style='FontName=Lato,FontSize=17,Bold=1,Outline=2,Shadow=0,MarginV=25,MarginL=45,MarginR=45'
    ff('-threads','5','-i',clean,'-vf',f"subtitles={OUT}/{NAME}.srt:force_style='{style}'",
       '-c:v','libx264','-threads','7','-preset','ultrafast','-crf','18','-c:a','copy',
       '-video_track_timescale','30000','-movflags','faststart',OUT/f'{NAME}.mp4')


def boundary_checks(rows, master):
    """Compare both sides of each finished cut to the independently encoded units."""
    paths = [Path(p) for p in re.findall(r"file '([^']+)'",(WORK/'lista.txt').read_text())]
    def decode(path, start, count):
        raw = subprocess.check_output(['ffmpeg','-v','error','-threads','2','-ss',f'{start/30:.9f}',
                                      '-i',str(path),'-frames:v',str(count),'-vf','scale=320:180',
                                      '-threads','1','-f','rawvideo','-pix_fmt','rgb24','-'])
        return np.frombuffer(raw,np.uint8).reshape(count,180,320,3)
    report=[]
    for i,row in enumerate(rows[1:],1):
        cut=row['start_frame']
        actual=decode(master,cut-23,46)
        first=decode(paths[i-1],rows[i-1]['frames']-23,23)
        second=decode(paths[i],0,23)
        assert np.array_equal(actual[:23],first) and np.array_equal(actual[23:],second), row['id']
        report.append({'from':rows[i-1]['id'],'to':row['id'],'frame':cut,'seconds':cut/30,
                       'compared_frames':46,'exact_pre_post':True})
    v03.write_json(OUT/'limites.json',report)
    with wave.open(str(WORK/'mix.wav'),'rb') as mix, wave.open(str(ROOT/'work/v03/mezcla.wav'),'rb') as old:
        for row in rows:
            if 'clip' in row:
                begin=row['start_frame']*1600
                mix.setpos(begin)
                old.setpos(begin)
                assert mix.readframes(row['frames']*1600)==old.readframes(row['frames']*1600)
    original=(OLD/'EL_TUNEL_V03.srt').read_text().rstrip()
    assert (OUT/f'{NAME}.srt').read_text().startswith(original+'\n\n')
    return report


def measure_scores(rows,master):
    original=json.loads((ROOT/'work/v02/edl.json').read_text())
    older={r['id']:r for r in original}
    music=[]
    for r in rows:
        if 'card' not in r:
            continue
        name=r['id']
        old=older.get(name)
        a=r['start_frame']/30
        n=r['frames']/30
        v3row=next(x for x in json.loads((OLD/'edl.json').read_text()) if x['id']==name)
        music.append([name, loud(v03.MASTER,old['start_frame']/30,old['frames']/30) if old else None,
                      loud(REFERENCE,v3row['start_frame']/30,n),loud(master,a,n)])
    return music


def validate(rows):
    total=sum(r['frames'] for r in rows)
    files=[OUT/f'{NAME}{suffix}.mp4' for suffix in ('_LIMPIO','')]
    with ThreadPoolExecutor(2) as pool:
        checks=list(pool.map(lambda f:audit.validate(f,total),files))
    def packets(path):
        cmd=['ffprobe','-v','error','-select_streams','v','-show_packets','-show_entries',
             'packet=pts,data_hash','-show_data_hash','sha256','-of','json',str(path)]
        packets=json.loads(subprocess.check_output(cmd))['packets']
        return [p['data_hash'] for p in sorted(packets,key=lambda p:int(p['pts']))]
    before,after=map(packets,(REFERENCE,files[0]))
    for r in rows:
        if 'clip' in r or ('blooper' in r and r['id']!='extra-cierre'):
            a=r['start_frame']
            b=a+r['frames']
            assert before[a:b]==after[a:b],r['id']
    boundary_checks(rows,files[0])
    music=measure_scores(rows,files[0])
    v03.write_json(OUT/'auditoria.json',{'masters':checks,'music_I_V02_V03_V031':music,
                   'unchanged_dialogue_frames':sum(r['frames'] for r in rows if 'clip' in r)})

    reports(OUT,OLD,rows)


if __name__=='__main__':
    stage=argparse.ArgumentParser()
    stage.add_argument('stage',choices=['prepare','review','build','audit'])
    action=stage.parse_args().stage
    WORK.mkdir(parents=True,exist_ok=True)
    (OUT/'musica').mkdir(parents=True,exist_ok=True)
    render.WORK=WORK
    render.CONFIG.update(json.loads((ROOT/'config/identidad-v03.local.json').read_text()))
    render.VIDEO=['superfast' if x=='veryfast' else x for x in render.VIDEO]
    {'prepare':prepare,'review':review,'build':build,'audit':validate}[action](timeline())
