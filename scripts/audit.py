"""Independently verify delivery files and create private contact sheets."""
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import json
import re
import subprocess

from PIL import Image, ImageDraw

from render import ROOT, WORK, OUT, SUB, NAME, FPS
from subtitles import seconds


def run(*command):
    result = subprocess.run(command,cwd=ROOT,check=True,capture_output=True,text=True)
    return result.stdout, result.stderr


def probe(path):
    raw,_ = run('ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path))
    return json.loads(raw)


def contact(path, rows):
    folder = WORK/'qa'
    folder.mkdir(exist_ok=True)
    moments = [(row['id'], (row['start_frame']+min(row['frames']//2,50))/FPS) for row in rows]
    moments += [('subtítulo', 17),('subtítulo',225),('reflexión',458)]
    tile = (384,216)
    sheet = Image.new('RGB',(tile[0]*4,246*((len(moments)+3)//4)), '#15171B')
    draw = ImageDraw.Draw(sheet)
    for i,(name,at) in enumerate(moments):
        still = folder/f'{i:02d}-{name}.jpg'
        run('ffmpeg','-v','error','-y','-ss',str(at),'-i',str(path),'-frames:v','1','-vf','scale=384:216','-threads','1',str(still))
        x, y = (i%4)*tile[0], (i//4)*246
        with Image.open(still) as image:
            sheet.paste(image,(x,y))
        draw.text((x+6,y+220),f'{at:07.2f}s  {name}',fill='#E9E2D4')
    sheet.save(folder/'hoja-contacto.jpg',quality=93)


def validate(path, expected_frames):
    metadata = probe(path)
    video, audio = [next(s for s in metadata['streams'] if s['codec_type']==kind) for kind in ('video','audio')]
    assert (video['width'],video['height'],video['codec_name'],video['pix_fmt'],video.get('sample_aspect_ratio', '1:1')) == (1920,1080,'h264','yuv420p','1:1')
    assert video['r_frame_rate']=='30/1'
    assert abs(float(video['duration'])*FPS-expected_frames) <= 1
    assert int(video['nb_frames'])==expected_frames
    raw,_ = run('ffprobe','-v','error','-select_streams','v:0','-show_entries',
                'packet=pts,duration','-of','json',str(path))
    packets = json.loads(raw)['packets']
    tick = Fraction(1, FPS)/Fraction(video['time_base'])
    assert tick.denominator == 1
    step = int(tick)
    assert len(packets) == expected_frames
    assert sorted(int(packet['pts']) for packet in packets) == list(range(0,expected_frames*step,step))
    assert all(int(packet['duration']) == step for packet in packets)
    assert (audio['codec_name'],audio['sample_rate'],audio['channels']) == ('aac','48000',2)
    assert abs(float(audio['duration'])-expected_frames/FPS)<.1
    _, log = run('ffmpeg','-hide_banner','-nostdin','-xerror','-threads','3','-i',str(path),
                 '-filter_threads','2','-vf','blackdetect=d=0.15:pix_th=0.055:pic_th=0.98',
                 '-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-')
    objective = json.loads(re.findall(r'\{[^{}]+\}',log)[-1])
    black = [line.strip() for line in log.splitlines() if 'black_start:' in line]
    assert abs(float(objective['input_i'])+16) <= 1
    assert float(objective['input_tp']) <= -1
    unexpected = []
    for interval in black:
        bounds = re.search(r'black_start:([\d.]+) black_end:([\d.]+)',interval)
        if not bounds or float(bounds[1]) > .05 or float(bounds[2]) > .65:
            unexpected.append(interval)
    assert not unexpected, unexpected
    return {'duration':metadata['format']['duration'],'video_frames':video['nb_frames'],
            'rate':video['avg_frame_rate'],'integrated_lufs':objective['input_i'],
            'true_peak_dbtp':objective['input_tp'],'black_intervals':black,'full_decode':True}


def main():
    rows = json.loads((WORK/'edl.json').read_text())
    frames = sum(row['frames'] for row in rows)
    assert frames < 12*60*FPS
    file = SUB/f'{NAME}.srt'
    old_end = 0
    captions = file.read_text().strip().split('\n\n')
    for i,chunk in enumerate(captions,1):
        number, interval, *lines = chunk.splitlines()
        a,b = map(seconds,interval.split(' --> '))
        assert int(number)==i
        assert old_end <= a < b <= frames/FPS+.001
        assert len(lines) <= 2 and all(len(line) <= 41 for line in lines)
        old_end = b
    files = [OUT/f'{NAME}_{suffix}.mp4' for suffix in ('LIMPIO','SUBTITULADO')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        images = pool.submit(contact,files[1],rows)
        results = list(pool.map(lambda path: validate(path,frames),files))
        images.result()
    audio_hashes = [run('ffmpeg','-v','error','-i',str(path),'-map','0:a:0',
                        '-c','copy','-f','hash','-hash','sha256','-')[0].strip() for path in files]
    assert audio_hashes[0] == audio_hashes[1]
    for result,path in zip(results,files):
        result['file'] = path.name
    report = {'deliveries':results,'caption_count':len(captions),'edl_frames':frames,
              'audio_packet_hash':audio_hashes[0]}
    (WORK/'qa/audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
