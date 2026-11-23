"""Assemble frame-exact video and normalize the uninterrupted episode mix."""
import json
import re

import render


def assemble(segments, rows, frames):
    work, out = render.WORK, render.OUT
    concat = work/'concat.txt'
    concat.write_text(''.join(
        f"file '{s.relative_to(work)}'\nduration {r['frames']/30:.8f}\n"
        for s,r in zip(segments,rows,strict=True)))
    wav = work/'dialogo.wav'
    render.ff('-v','error','-f','concat','-safe',0,'-i',concat,'-vn',
              '-af','aresample=async=1:first_pts=0','-c:a','pcm_s16le',wav)
    settings = render.CONFIG['audio']
    loud = f"loudnorm=I={settings['lufs']}:TP={settings['peak']}:LRA=11"
    log = render.ff('-i',wav,'-af',loud+':print_format=json','-f','null','-',capture=True)
    values = json.loads(re.findall(r'\{[^{}]+\}',log)[-1])
    normal = (loud+f":measured_I={values['input_i']}:measured_TP={values['input_tp']}"
              f":measured_LRA={values['input_lra']}:measured_thresh={values['input_thresh']}"
              f":offset={values['target_offset']}:linear=true")
    duration=f'{frames/30:.8f}'
    temp=work/'clean.mp4'
    render.ff('-v','error','-f','concat','-safe',0,'-i',concat,'-i',wav,'-map','0:v','-map','1:a',
              '-c:v','copy','-af',normal+',aresample=48000,apad','-c:a','aac','-b:a','192k',
              '-t',duration,'-video_track_timescale',30000,'-movflags','+faststart',temp)
    temp.replace(out/f'{render.NAME}_LIMPIO.mp4')
