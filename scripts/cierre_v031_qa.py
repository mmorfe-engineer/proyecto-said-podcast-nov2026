"""Verify every retained picture and the approved audio edit before delivery."""
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import wave
import numpy as np

from cierre_v031 import REF, OUT, WORK, ROOT, NAME
from audit import validate


def frames(path, close):
    # Compare the entire decoded YUV image; ignore precisely the authorized
    # rectangle during the two institutional cards in each version.
    graph=f"drawbox=1664:80:176:176:color=black:t=fill:enable='lt(n,510)+gte(n,{close})'"
    raw=subprocess.check_output(['ffmpeg','-v','error','-xerror','-threads','3','-i',str(path),
        '-map','0:v','-vf',graph,'-filter_threads','1','-threads:v','1','-f','framecrc','-'],text=True)
    return [s.rsplit(',',1)[-1].strip() for s in raw.splitlines() if s and not s.startswith('#')]


def audio(path):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a','-f','s16le','-'])
    return np.frombuffer(raw,'<i2').reshape(-1,2)


def main():
    old=json.loads((REF/'edl.json').read_text())
    new=json.loads((OUT/'edl.json').read_text())
    cut,close=old[-2]['start_frame'],old[-1]['start_frame']
    n=cut+old[-1]['frames']
    assert new==old[:-2]+[{**old[-1],'start_frame':cut}]
    checks={}
    for suffix in ('_LIMPIO',''):
        name=f'{NAME}{suffix}.mp4'
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(frames,REF/name,close)
            b=pool.submit(frames,OUT/name,cut)
            before,after=a.result(),b.result()
        expected=before[:cut]+before[close:]
        assert len(after)==len(expected)==n
        for i,(a,b) in enumerate(zip(expected,after)):
            assert a==b, (name,i,a,b)
        checks[name]=validate(OUT/name,n)
    source=audio(REF/f'{NAME}.mp4')
    result=audio(OUT/f'{NAME}.mp4')
    assert np.array_equal(result,audio(OUT/f'{NAME}_LIMPIO.mp4'))
    border=cut*1600
    delta=np.flatnonzero(np.any(source[:border]!=result[:border],axis=1))
    first=int(delta[0]) if len(delta) else border
    assert first>=border-4096, (first,border)
    # The cut shifts the final AAC window grid by half a packet. Verify its
    # underlying PCM exactly and measure the reconstructed music against V03.1.
    with wave.open(str(ROOT/'work/v03_1/mix.wav'),'rb') as src, wave.open(str(WORK/'corte.wav'),'rb') as dst:
        assert src.readframes(border)==dst.readframes(border)
        src.setpos(close*1600)
        assert src.readframes(old[-1]['frames']*1600)==dst.readframes(old[-1]['frames']*1600)
    a=source[close*1600:close*1600+old[-1]['frames']*1600].astype(float).ravel()
    b=result[border:n*1600].astype(float).ravel()
    correlation=float(np.corrcoef(a,b)[0,1])
    assert correlation>.995
    checks['audio']={'identical_decoded_samples_before_join':first,'final_music_correlation':correlation}
    checks['frames_compared_per_master']=n
    (OUT/'auditoria-final.json').write_text(json.dumps(checks,indent=2)+'\n')


if __name__=='__main__':
    main()
