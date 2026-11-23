"""Audit V02 media, caption timing and coverage of retained source ranges."""
from concurrent.futures import ThreadPoolExecutor
import json

from audit import validate, contact, run
from subtitles import seconds
from v02 import ROOT, WORK, OUT, SUB, NAME
from v02_subtitles import PROHIBITED


def audit(rows,total):
    assert total>=600*30
    prior_edl=ROOT/'work/rc/edl.json'
    old=json.loads(prior_edl.read_text()) if prior_edl.exists() else []
    sources={n:[row for row in rows if row.get('clip')==n] for n in range(1,9)}
    for n,retained in sources.items():
        assert retained
        for item in [row for row in old if row.get('clip')==n]:
            assert any(row['in']<=item['in']+.15 and row['out']>=item['out']-.15 for row in retained), item['id']
    assert {'a','b','c'} <= {row['blooper'] for row in rows if 'blooper' in row}
    assert rows[-1]['card']=='end'
    for row in rows:
        if 'deck' in row:
            assert len(row['deck'].split())<=20
    srt=(SUB/f'{NAME}.srt').read_text()
    assert not PROHIBITED.search(srt) and '[' not in srt
    count=0
    prior=0
    for count,item in enumerate(srt.strip().split('\n\n'),1):
        idx,bounds,*lines=item.splitlines()
        a,b=map(seconds,bounds.split(' --> '))
        assert int(idx)==count and prior<=a<b<=total/30+.001
        assert 1<=len(lines)<=2 and max(map(len,lines))<=41
        prior=b
    files=[OUT/f'{NAME}_LIMPIO.mp4',OUT/f'{NAME}.mp4']
    with ThreadPoolExecutor(max_workers=3) as pool:
        sheet=pool.submit(contact,files[1],rows)
        checks=list(pool.map(lambda file: validate(file,total),files))
        sheet.result()
    hashes=[run('ffmpeg','-v','error','-i',str(f),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-')[0]
            for f in files]
    assert hashes[0]==hashes[1]
    original=run('sha256sum','-c',str(WORK/'preservacion.sha256'))[0]
    info={'masters':checks,'captions':count,'frames':total,
          'new_bloopers':['a','b','c'],'preserved_files':len(original.splitlines()),
          'compared_with_v01':bool(old),'source_windows':{str(i):[[x['in'],x['out']] for x in a] for i,a in sources.items()}}
    (WORK/'qa/audit.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(info,ensure_ascii=False,indent=2))
