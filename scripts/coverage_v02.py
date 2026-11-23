"""Generate an edition-to-edition coverage matrix from locally annotated ranges."""
import json

from v02 import ROOT, WORK


def covered(spans, edits):
    return sum(max(0,min(b,row['out'])-max(a,row['in'])) for a,b in spans for row in edits)


def build():
    annot=json.loads((WORK/'participantes.json').read_text())
    ident=json.loads((ROOT/'config/identidad.local.json').read_text())['participants']
    old=json.loads((ROOT/'work/rc/edl.json').read_text())
    new=json.loads((WORK/'edl.json').read_text())
    names=list(ident)
    lines=['# Matriz privada de participación · V02','',
           'Los intervalos de turnos son aproximados. Las atribuciones provisionales y los turnos sin atribución requieren cotejo visual y sonoro continuo. Los totales de fuente y los solapamientos con la EDL se calcularon a partir de las ventanas conservadas.','',
           '| Fuente | Original / V01 / V02 por integrante, en segundos | Estado |',
           '|---|---|---|']
    detail=[]
    for clip,people in annot.items():
        a,b=([row for row in edition if str(row.get('clip'))==clip] for edition in (old,new))
        metrics=[]
        for person in names:
            notes=people[person]
            spans=notes['spans']
            item=(sum(y-x for x,y in spans),covered(spans,a),covered(spans,b))
            shown=' / '.join(f'{val:.2f}' for val in item) if spans else 'sin estimación'
            metrics.append(f'{ident[person]["name"]} {shown}')
            detail.append({'source':int(clip),'participant':ident[person]['name'],
                           'estimates_sec':item if spans else None,'recovered_sec':max(0,item[2]-item[1]) if spans else None,
                           'source_ranges':spans,'confidence':notes['status']})
        lines.append(f'| {clip} | {" · ".join(metrics)} | Turnos completos conservados dentro de las ventanas editoriales. |')
    lines.extend(['','## Evidencia y reservas',''])
    for item in detail:
        lines.append(f'- Toma {item["source"]}, {item["participant"]}. {item["confidence"]} '
                     f'Referencias de origen {item["source_ranges"] or "pendientes de atribución"}.')
    (WORK/'matriz_participacion.md').write_text('\n'.join(lines)+'\n')
    (WORK/'matriz_participacion.json').write_text(json.dumps(detail,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    build()
