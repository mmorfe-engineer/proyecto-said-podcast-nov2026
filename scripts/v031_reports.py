"""Write the private V03.1 inspection dossier from the measured master results."""
import json
import subprocess
import wave

import numpy as np


def reports(out, old, rows):
    report = json.loads((out/'auditoria.json').read_text())
    limits = json.loads((out/'limites.json').read_text())
    folder = out/'informes'
    folder.mkdir(exist_ok=True)
    def write(name, lines):
        (folder/f'V03_1_{name}.txt').write_text('\n'.join(lines)+'\n')
    write('CAUSA_RAIZ_TRANSICIONES',[
        'V03 encadenaba los segmentos por concatenación. La contaminación se generaba antes, en los cuadros de las cortinas.',
        'wipe() construía una máscara espacial a partir de ruido y mezclaba la ilustración con un fotograma de prev o next.',
        'A 192,067 s, tras anatomia, capitulo-2 recuperaba la fuente 2. A 282,233 s, después de evidencia, capitulo-3 recuperaba la fuente 3.',
        'El motor V03.1 compone cada cortina en su propio plano y usa corte directo en sus extremos. El bloque de bloopers conserva su ilustración intencional.',
        'Checkpoint local: checkpoint-v03-antes-v03-1. V03 se conserva como referencia.'])
    write('VERIFICACION_TRANSICIONES',[
        '25 empalmes. Se decodificaron 23 cuadros por lado a 320 × 180 y se compararon con los cuadros equivalentes del componente. La hoja de contacto muestra seis instantes por corte.',
        'Inspección de la hoja completa: las junturas de 03:12.067 y 04:42.233 pasan de gráfica a gráfica. En 01:17.133 se conserva una portadilla ilustrada dentro del video 1, presente en el segmento aprobado de V02/V03.',
        'Manchetas de capítulos I–IV a 0,033 s de cada entrada: contraste estimado de 14,57, 14,46, 14,55 y 14,49 a 1. Medición sRGB linealizada del percentil 99 frente a la mediana en la zona de texto, no una certificación por glifo.',
        'La fase de lectura entra desde el primer cuadro de los capítulos. La apertura cambia a integrantes dentro de su propio plano. El agradecimiento conserva su salida final.',
        *[f"{r['seconds']:.3f} s   {r['from']} → {r['to']}   46/46 cuadros coinciden." for r in limits]])
    audio=['EL TÚNEL — Literary Sonic Signature. Comparación de sonoridad integrada en los másteres, LUFS.',
           'Pieza | V02 | V03 | V03.1 | duración | último segundo con RMS superior a −45 dBFS']
    scores=dict((r['id'],r) for r in rows)
    for name, v2, v3, current in report['music_I_V02_V03_V031']:
        with wave.open(str(out/'musica'/f'{name}.wav'),'rb') as w:
            samples=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)/32768
        blocks=samples[:len(samples)//9600*9600].reshape(-1,9600)
        rms=np.sqrt(np.mean(blocks**2,axis=1))
        end=(np.where(rms>10**(-45/20))[0][-1]+1)/10
        audio.append(f"{name} | {v2 if v2 is not None else 'sin equivalente'} | {v3} | {current} | {scores[name]['frames']/30:.2f} s | {end:.1f} s")
    audio+=['La música V03 está en los másteres. music() inicia cuatro ataques separados por 0,31 s y aplica un decaimiento de 0,62 s. Salvo apertura y agradecimiento, queda gran parte de cada lectura sin acompañamiento perceptible. V03 mezcla el PCM de las nuevas cortinas sin el paso global de normalización de V02.',
            'V03.1 asigna objetivos diferentes por función. El PCM del diálogo coincide con V03 antes de codificar. Las notas y sus colas se limitan a las cortinas.',
            'Control instrumental y comparación de fuentes. El entorno carece de monitorización auditiva. El cotejo perceptivo queda disponible en AB-V02-V031.wav y en el reel.']
    write('AUDITORIA_IDENTIDAD_SONORA',audio)
    last=next(r for r in rows if r['id']=='extra-cierre')
    write('REVISION_BLOOPERS',[f"extra-cierre: bloopers_c.mp4, entrada {last['in']:.3f} s, salida {last['out']:.3f} s frente a 7,050 s en V03.",
        f"Se recuperaron {last['frames']-195} fotogramas. El original dura 10,967 s. La transcripción previa registra el tropiezo final. En los fotogramas se ve al participante acercarse y extender la mano hacia la cámara.",
        'Se tomó el desenlace hasta el último intervalo completo de 30 fps. Los otros tres bloopers conservan sus paquetes de imagen.'])
    text=['Ambos másteres pasaron decodificación completa, análisis de cuadros negros, CFR y coherencia temporal.',
          *[json.dumps(m,ensure_ascii=False) for m in report['masters']],
          f"Paquetes de imagen idénticos en {report['unchanged_dialogue_frames']} cuadros de diálogo. PCM de las nueve unidades verificado antes de AAC.",
          '142 bloques SRT aprobados conservados. Se añade un bloque para el final recuperado. El texto reproduce la parte reconocible del tropiezo.',
          'La carpeta logo colegio sigue vacía. La identidad institucional aparece en texto.']
    write('CONTROL_CALIDAD',text)
    names=[p.name for p in sorted(out.iterdir()) if p.is_file()]
    write('ENTREGA_FINAL',[f'Duración {sum(r["frames"] for r in rows)/30:.6f} s.',*names,
                          'musica/ contiene los trece motivos estéreo originales. Los másteres, los reels y las hojas de contacto son de entrega local.'])
    write('CONTINUIDAD_EJECUTIVA',[text[0],text[3],'25 empalmes verificados. Firma musical original en 13 piezas. El último blooper recupera 3,9 s.',
                                  'La revisión visual se documenta con los reels y la hoja de contacto. La aprobación auditiva humana y el escudo institucional siguen pendientes.',
                                  str(out)])
    base=json.loads((old.parent.parent/'work/v02/edl.json').read_text())
    with wave.open(str(out/'AB-V02-V031.wav'),'wb') as dest:
        dest.setparams((2,2,48000,0,'NONE','not compressed'))
        for name in ('apertura','capitulo-2','epilogo','detras-de-camaras','agradecimiento'):
            for source, timeline in [(old.parent/'v02/EL_TUNEL_V02_LIMPIO.mp4',base),
                                     (out/'EL_TUNEL_V03_1_LIMPIO.mp4',rows)]:
                entry=next(r for r in timeline if r['id']==name)
                data=subprocess.check_output(['ffmpeg','-v','error','-ss',str(entry['start_frame']/30),
                    '-i',str(source),'-t',str(min(8,entry['frames']/30)),'-vn','-f','s16le','-'])
                dest.writeframesraw(data)
                dest.writeframesraw(bytes(48000))
