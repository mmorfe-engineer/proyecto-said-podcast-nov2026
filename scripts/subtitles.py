"""Map edited source captions to the episode timeline."""
import json
import re
import math

from render import ROOT, WORK, SUB, NAME, FPS, prepare_timeline, CONFIG


def seconds(stamp):
    h, m, s, ms = map(int, re.split('[:,]', stamp))
    return h*3600 + m*60 + s + ms/1000


def srt_stamp(value):
    minutes, ms = divmod(round(value*1000),60000)
    hours, minutes = divmod(minutes,60)
    sec, ms = divmod(ms,1000)
    return f'{hours:02d}:{minutes:02d}:{sec:02d},{ms:03d}'


def chunks(text):
    words = text.split()
    count = max(1, math.ceil(len(text)/76))
    result = []
    while words:
        if count == 1:
            take = len(words)
        else:
            target = len(' '.join(words))/count
            take = min(range(1,len(words)), key=lambda n: abs(len(' '.join(words[:n]))-target))
        fragment = words[:take]
        candidate = ' '.join(fragment)
        if len(candidate) <= 41:
            result.append(candidate)
        else:
            cuts = [n for n in range(1,len(fragment))
                    if max(len(' '.join(fragment[:n])),len(' '.join(fragment[n:])))<=41]
            if not cuts:
                count += 1
                continue
            split = min(cuts, key=lambda n: abs(len(' '.join(fragment[:n]))-len(candidate)/2))
            result.append(' '.join(fragment[:split])+'\n'+' '.join(fragment[split:]))
        words = words[take:]
        count = max(1,count-1)
    return result


def build():
    curated = json.loads((ROOT/'config/dialogo.json').read_text())
    prepare_timeline()
    cues = []
    flagged = []
    for item in CONFIG['timeline']:
        if 'card' in item:
            continue
        base = item['start_frame']/FPS
        if 'clip' in item:
            clip = str(item['clip'])
            srt = (ROOT/'work/transcripciones'/f'podcast_{clip}.srt').read_text()
            matches = re.findall(r'(?m)^(\d+)\n([\d:,]+) --> ([\d:,]+)',srt)
            rows = []
            for num,start,end in matches:
                if num not in curated[clip]:
                    continue
                edit = curated[clip][num]
                rows.append(edit if isinstance(edit,list) else (seconds(start),seconds(end),edit))
        else:
            rows = curated['extra'][str(item['blooper'])]
        for start,end,dialogue in rows:
            # Each EDL selection owns its source range. The teaser may intentionally reuse
            # a little pre-roll, but an overlapping cue belongs to its first complete use.
            if item['id']=='gancho' and start>=item['out']:
                continue
            if item['id']=='violencia' and start<item['in']:
                continue
            visible_start = max(start,item['in'])
            visible_end = min(end,item['in']+item['frames']/FPS)
            if visible_end-visible_start < .55:
                continue
            a = visible_start-item['in']+base
            b = visible_end-item['in']+base
            if '[' in dialogue:
                flagged.append({'segment':item['id'],'source_time':start,'episode_time':a,'reason':dialogue})
            parts = chunks(dialogue)
            weights = [len(part) for part in parts]
            pos = a
            for part,weight in zip(parts,weights):
                next_pos = pos + (b-a)*weight/sum(weights)
                cues.append((pos,next_pos,part))
                pos = next_pos
    SUB.mkdir(exist_ok=True)
    srt = '\n'.join(f'{i}\n{srt_stamp(a)} --> {srt_stamp(b)}\n{text}\n'
                    for i,(a,b,text) in enumerate(cues,1))
    (SUB/f'{NAME}.srt').write_text(srt)
    vtt = 'WEBVTT\n\n' + '\n'.join(
        f'{srt_stamp(a).replace(",",".")} --> {srt_stamp(b).replace(",",".")}\n{text}\n'
        for a,b,text in cues
    )
    (SUB/f'{NAME}.vtt').write_text(vtt)
    (WORK/'subtitulos_revision.json').write_text(json.dumps(flagged,ensure_ascii=False,indent=2))
    print(f'{len(cues)} cues · {len(flagged)} fragmentos señalados')


if __name__=='__main__':
    build()
