"""Build a deterministic 1080p podcast from the editorial configuration."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess

from PIL import Image

from graphics import SIZE, card, charcoal, label, paper, hex_rgb, score

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT/'work/rc'
OUT = ROOT/'renders'
SUB = ROOT/'subtitles'
FPS = 30
CONFIG = json.loads((ROOT/'config/episodio.json').read_text())
RATE = CONFIG['audio']['sample_rate']
NAME = 'EL_TUNEL_RC1'
VIDEO = ['-c:v','libx264','-preset','veryfast','-crf','18','-threads','3','-pix_fmt','yuv420p',
         '-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709']


def ff(*args, capture=False):
    result = subprocess.run(['ffmpeg','-nostdin','-hide_banner','-y','-filter_threads','2',
                             '-filter_complex_threads','2',*map(str,args)], cwd=ROOT, check=True,
                            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                            stderr=subprocess.PIPE, text=capture, timeout=420)
    return result.stderr


def source(item):
    if 'clip' in item:
        return ROOT / 'podcast_videos_raw' / f'podcast_{item["clip"]}.mp4'
    return ROOT / 'bloopers' / f'bloopers_{item["blooper"]}.mp4'


def grab(clip_number, at, target):
    ff('-v','error','-ss',at,'-i',source({'clip':clip_number}),'-frames:v',1,target)
    with Image.open(target) as image:
        return image.convert('RGB')


def prepare(item, folder):
    if 'card' in item:
        portrait = grab(*item['portrait'], folder/'portrait.jpg') if 'portrait' in item else None
        card(CONFIG,item,portrait=portrait).save(folder/'card.png')
        score(folder/'music.wav',item['frames']/FPS,item['card'],RATE)
    for n, (_, person) in enumerate(item.get('labels', [])):
        person = CONFIG['participants'][person]
        label(CONFIG,person['name'] or person['role'],person['role'] if person['name'] else '').save(folder/f'label{n}.png')
    if 'callout' in item:
        label(CONFIG,item['callout'][1]).save(folder/'callout.png')
    if 'cover' in item:
        participant = grab(*item['cover'],folder/'cover-source.jpg')
        background = paper(hex_rgb(CONFIG['palette']['ivory']), False).copy()
        background.paste(charcoal(participant,CONFIG), (510,215))
        background.save(folder/'cover.png')


def segment(item):
    path = source(item) if 'card' not in item else None
    material = [CONFIG['palette'],CONFIG['fonts'],CONFIG['participants'],CONFIG['look'],CONFIG['audio'],
                CONFIG['title'],CONFIG['subtitle'],CONFIG['institution'],CONFIG['edition'],item,
                path.stat().st_mtime_ns if path else None,
                [(ROOT/'scripts'/file).stat().st_mtime_ns for file in ('render.py','graphics.py')]]
    key = hashlib.sha256(json.dumps(material,sort_keys=True).encode()).hexdigest()[:12]
    folder = WORK/'segments'/f'{item["id"]}-{key}'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder/'segment.mov'
    if target.exists():
        return target
    prepare(item,folder)
    duration = item['frames']/FPS
    if 'card' in item:
        animation = ("zoompan=z='1+0.025*(1-cos(PI*on/"+str(item['frames'])+"))/2'"
                     ":x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=30")
        if item['card'] == 'open':
            art = []
            (folder/'opening').mkdir(exist_ok=True)
            for frame in range(48):
                progress = min(1,frame/39)
                shown = card(CONFIG,item,progress)
                fade = min(1,frame/20)
                Image.blend(Image.new('RGB',SIZE,CONFIG['palette']['coal']),shown,fade).save(
                    folder/'opening'/f'{frame:03d}.jpg',quality=91)
            art = ['-framerate','12','-i',folder/'opening/%03d.jpg','-i',folder/'music.wav',
                   '-vf',f'tpad=stop_mode=clone:stop_duration=5,fps=30,{animation},scale=in_range=full:out_range=limited,format=yuv420p']
        else:
            art = ['-loop',1,'-framerate',30,'-i',folder/'card.png','-i',folder/'music.wav','-vf',animation]
        args = [*art,'-map','0:v','-map','1:a',
                '-af',f'volume={2.0 if item["card"] in ("open","close") else -1.0}dB']
    else:
        is_vertical = item.get('blooper') == 6
        brightness, contrast, saturation = CONFIG['look'].get(str(item.get('clip')), (0,1,.95))
        picture = (f'fps=30:start_time=0,eq=brightness={brightness}:contrast={contrast}:saturation={saturation},'
                   'scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos,'
                   'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x15171B,setsar=1,tpad=stop_mode=clone:stop_duration=0.1')
        if item.get('zoom',1)>1 and not is_vertical:
            factor = item['zoom']
            picture += (f",crop=w={int(1920/factor)//2*2}:h={int(1080/factor)//2*2}:"
                        "x='(iw-ow)*(0.42+0.1*sin(t/5))':y='(ih-oh)*0.38',scale=1920:1080:flags=lanczos")
        audio = ('highpass=f=75,lowpass=f=11500,afftdn=nr=5:nf=-43:tn=1,'
                 'aformat=sample_rates=48000:channel_layouts=stereo,'
                 'acompressor=threshold=0.055:ratio=2.25:attack=11:release=120')
        measure = ff('-ss',item['in'],'-t',duration,'-i',path,'-vn','-af',
                     audio+',loudnorm=I=-18:TP=-2:LRA=12:print_format=json','-f','null','-',capture=True)
        stats = json.loads(re.findall(r'\{[^{}]+\}',measure)[-1])
        gain = max(-5,min(17,-17.5-float(stats['input_i'])))
        audio += (f',volume={gain:.3f}dB,alimiter=limit=0.83:level=false:latency=1,'
                  f'afade=t=in:d=0.035,afade=t=out:st={duration-.06:.4f}:d=0.06,apad=whole_dur={duration:.6f}')
        (folder/'audio.json').write_text(json.dumps({**stats,'gain_db':gain},indent=2))
        args = ['-threads',2,'-ss',item['in'],'-t',f'{duration+.1:.6f}','-i',path]
        filters = ['[0:v]'+picture+'[v0]']
        overlays = []
        if 'cover' in item:
            overlays.append((folder/'cover.png',0,.48,0,0,.0,.27))
        for n,(at,_) in enumerate(item.get('labels',[])):
            overlays.append((folder/f'label{n}.png',at,4.0,92,112,.27,.32))
        if 'callout' in item:
            overlays.append((folder/'callout.png',item['callout'][0],3.8,92,105,.26,.33))
        for n,(image,at,length,x,y,fade_in,fade_out) in enumerate(overlays,1):
            args += ['-loop',1,'-framerate',30,'-i',image]
            chain = f'[{n}:v]format=rgba'
            if fade_in:
                chain += f',fade=t=in:st={at}:d={fade_in}:alpha=1'
            chain += f',fade=t=out:st={at+length-fade_out}:d={fade_out}:alpha=1[o{n}]'
            filters += [chain, f"[v{n-1}][o{n}]overlay={x}:{y}:enable='between(t,{at},{at+length})'[v{n}]"]
        picture_file = folder/'picture.mov'
        sound_file = folder/'voice.wav'
        ff('-v','error',*args,'-filter_complex',';'.join(filters),'-map',f'[v{len(overlays)}]',
           '-an','-frames:v',item['frames'],*VIDEO,'-video_track_timescale',30000,picture_file)
        ff('-v','error','-ss',item['in'],'-t',f'{duration+.12:.6f}','-i',path,'-vn','-af',
           audio+f',atrim=end_sample={item["frames"]*RATE//FPS}',
           '-ar',RATE,'-ac',2,'-c:a','pcm_s16le',sound_file)
        args = ['-i',picture_file,'-i',sound_file,'-map','0:v','-map','1:a']
    temp = folder/'building.mov'
    codec = VIDEO if 'card' in item else ['-c:v','copy']
    ff('-v','error',*args,'-t',f'{duration:.6f}',*codec,'-ar',RATE,'-ac',2,'-c:a','pcm_s16le',
       '-video_track_timescale',30000,temp)
    temp.replace(target)
    print(f'{item["id"]} · {item["frames"]} fotogramas',flush=True)
    return target


def prepare_timeline():
    frames = 0
    for item in CONFIG['timeline']:
        item['start_frame'] = frames
        if 'card' in item:
            duration = item['duration']
        else:
            duration = item['out']-item['in']
            media_duration = float(subprocess.check_output(
                ['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',source(item)]))
            if not 0 <= item['in'] < item['out'] <= media_duration:
                raise ValueError(f'Rango fuera del original: {item["id"]}')
        item['frames'] = round(duration*FPS)
        frames += item['frames']
    (WORK/'edl.json').write_text(json.dumps(CONFIG['timeline'],ensure_ascii=False,indent=2)+'\n')
    return frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['preview','clean','subtitled'])
    args = parser.parse_args()
    for folder in (WORK,OUT,SUB):
        folder.mkdir(parents=True,exist_ok=True)
    frames = prepare_timeline()
    rows = CONFIG['timeline']
    if args.stage == 'preview':
        for name in ('apertura','gancho','capitulo-2','capitulo-4','creditos','detras-de-camaras'):
            item = next(item for item in rows if item['id']==name)
            result = segment(item)
            ff('-v','error','-i',result,'-c:v','copy','-c:a','aac','-movflags','+faststart',
               OUT/f'{name}.mp4')
        card(CONFIG,rows[0]).resize((1280,720),Image.Resampling.LANCZOS).save(OUT/'thumbnail.jpg',quality=94)
        return
    if args.stage == 'subtitled':
        path = SUB/f'{NAME}.srt'
        temp = WORK/'subtitled.mp4'
        ff('-v','error','-threads','3','-i',OUT/f'{NAME}_LIMPIO.mp4','-vf',
           f"subtitles=subtitles/{path.name}:force_style='FontName=Lato,FontSize=17,Bold=1,Outline=2,Shadow=0,MarginV=25,MarginL=45,MarginR=45'",
           *VIDEO,'-c:a','copy','-movflags','+faststart',temp)
        temp.replace(OUT/f'{NAME}_SUBTITULADO.mp4')
        return
    with ThreadPoolExecutor(max_workers=2) as pool:
        segments = list(pool.map(segment,rows))
    concat = WORK/'concat.txt'
    concat.write_text(''.join(f"file '{s.relative_to(WORK)}'\nduration {r['frames']/FPS:.8f}\n" for s,r in zip(segments,rows)))
    raw_audio = WORK/'dialogo.wav'
    ff('-v','error','-f','concat','-safe',0,'-i',concat,'-vn','-c:a','pcm_s16le',raw_audio)
    audio = CONFIG['audio']
    analysis = f"loudnorm=I={audio['lufs']}:TP={audio['peak']}:LRA=11"
    measured = ff('-i',raw_audio,'-af',analysis+':print_format=json','-f','null','-',capture=True)
    marker = json.loads(re.findall(r'\{[^{}]+\}',measured)[-1])
    normalizer = (analysis+f":measured_I={marker['input_i']}:measured_TP={marker['input_tp']}"
                  f":measured_LRA={marker['input_lra']}:measured_thresh={marker['input_thresh']}"
                  f":offset={marker['target_offset']}:linear=true")
    temp = WORK/'clean.mp4'
    ff('-v','error','-f','concat','-safe',0,'-i',concat,'-i',raw_audio,'-map','0:v','-map','1:a',
       '-c:v','copy','-af',normalizer+',aresample=48000','-c:a','aac','-b:a','192k','-ar',RATE,
       '-t',f'{frames/FPS:.6f}','-video_track_timescale',30000,'-movflags','+faststart',temp)
    temp.replace(OUT/f'{NAME}_LIMPIO.mp4')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stderr.decode(errors='replace') if isinstance(error.stderr, bytes) else error.stderr)
        raise
