"""Inventory immutable local media and optionally generate private draft subtitles."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT/'work'


def media():
    return sorted((ROOT/'podcast_videos_raw').glob('*.mp4')) + sorted((ROOT/'bloopers').glob('*.mp4'))


def inventory():
    out = WORK/'inventario.json'
    rows = []
    for path in media():
        metadata = subprocess.check_output(['ffprobe','-v','error','-show_streams',
                                            '-show_format','-of','json',str(path)],text=True)
        with path.open('rb') as media_file:
            fingerprint = hashlib.file_digest(media_file,'sha256').hexdigest()
        details = json.loads(metadata)
        rows.append({'path':str(path.relative_to(ROOT)), 'sha256':fingerprint,
                     'duration':details['format']['duration'], 'streams':details['streams']})
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rows,indent=2)+'\n')
    print(f'{len(rows)} originales · {out.relative_to(ROOT)}')


def timestamp(seconds):
    millis = round(seconds*1000)
    hours, millis = divmod(millis,3600000)
    minutes, millis = divmod(millis,60000)
    seconds, millis = divmod(millis,1000)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}'


def transcribe(folder):
    from faster_whisper import WhisperModel
    model = WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=5,
                         local_files_only=True)
    folder.mkdir(parents=True,exist_ok=True)
    for path in media():
        target = folder/f'{path.stem}.srt'
        if target.exists():
            continue
        duration = float(subprocess.check_output(
            ['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',path]))
        segments,_ = model.transcribe(str(path),language='es',beam_size=2,vad_filter=True,
                                      condition_on_previous_text=False)
        cues = []
        for part in segments:
            a,b = round(part.start,2), min(round(part.end,2),duration)
            if a<b:
                cues.append(f'{len(cues)+1}\n{timestamp(a)} --> {timestamp(b)}\n{part.text.strip()}\n')
        target.write_text('\n'.join(cues))
        print(target.relative_to(ROOT),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--drafts',action='store_true',help='usa Faster Whisper y el modelo pequeño ya instalados')
    args = parser.parse_args()
    inventory()
    if args.drafts:
        transcribe(WORK/'transcripciones-nuevas')
