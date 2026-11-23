"""Apply reviewed dialogue edits to source cues, then conform to the V02 EDL."""
import json
import re

from subtitles import seconds, srt_stamp, chunks
from v02 import ROOT, WORK, SUB, NAME


PROHIBITED=re.compile(r'said[ -]+(?:podcast|proyecto)|proyecto said|inaudible|poco clar[oa]s?|incomprensibl',re.I)


def build(rows):
    base=json.loads((ROOT/'config/dialogo.json').read_text())
    edits=json.loads((ROOT/'config/dialogo-v02.json').read_text())
    for clip, changes in edits.items():
        base.setdefault(clip,{}).update(changes)
    encoded=[]
    omissions=[]
    for item in rows:
        if 'card' in item:
            continue
        if 'clip' in item:
            clip=str(item['clip'])
            text=(ROOT/'work/transcripciones'/f'podcast_{clip}.srt').read_text()
            stamps=re.findall(r'(?m)^(\d+)\n([\d:,]+) --> ([\d:,]+)',text)
            cues=[]
            for ident,a,b in stamps:
                if ident not in base[clip]:
                    continue
                edit=base[clip][ident]
                cues.append(edit if isinstance(edit,list) else [seconds(a),seconds(b),edit])
        else:
            cues=base['extra'][str(item['blooper'])]
        shift=item['start_frame']/30-item['in']
        for a,b,caption in cues:
            a=max(a,item['in'])
            b=min(b,item['in']+item['frames']/30)
            if b-a<.53:
                continue
            if not caption:
                omissions.append({'id':item['id'],'source_start':a,'source_end':b})
                continue
            if PROHIBITED.search(caption) or '[' in caption:
                raise ValueError(f'Candidato con anotación interna en {item["id"]}: {caption}')
            parts=chunks(caption)
            weights=[len(part) for part in parts]
            current=a+shift
            for part,weight in zip(parts,weights):
                end=current+(b-a)*weight/sum(weights)
                timing=f'{srt_stamp(current)} --> {srt_stamp(end)}'
                encoded.append(f'{len(encoded)+1}\n{timing}\n{part}\n')
                current=end
    (SUB/f'{NAME}.srt').write_text('\n'.join(encoded))
    (WORK/'notas-subtitulos.json').write_text(json.dumps(omissions,indent=2)+'\n')
    print(f'{len(encoded)} subtítulos. {len(omissions)} bloques omitidos del texto por cotejo pendiente.',flush=True)
