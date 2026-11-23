# El túnel · V03.1

V03.1 conserva la EDL académica de V03. Las cortinas reciben únicamente su propia ilustración y sus textos. Desde el primer cuadro se presenta una composición de lectura con los trazos en movimiento. La entrada a créditos de grupo cambia de composición dentro de la apertura. El fundido final pertenece al agradecimiento.

La partitura **El túnel — Literary Sonic Signature** se genera a 48 kHz estéreo con un cuerpo de piano amortiguado, un parcial de celesta y una resonancia breve. La apertura introduce re–la–fa–mi. Los capítulos usan tres notas con variaciones de altura e intervalo temporal. Las cápsulas espacian las notas a lo largo de la lectura. El epílogo reduce la intensidad, los bloopers aceleran la articulación y el agradecimiento resuelve en re. Cada pieza se mide y ajusta antes del conformado. El PCM de las conversaciones procede de la mezcla aprobada V03.

## Reproducción

Desde la raíz del proyecto, usar Python, Pillow, NumPy, FFmpeg con libass y FFprobe, las fuentes de V03 y los materiales locales conservados. Se requieren los másteres limpios V02/V03, sus EDL, el SRT V03, el manifiesto y los segmentos V02, la imagen de referencia de bloopers, el PCM aprobado de V03, el original del último blooper y la identidad local.

```bash
python3 scripts/v031.py prepare
python3 scripts/v031.py review
# Revisar reel-v031.mp4, comparativa.mp4 y limites.jpg antes del conformado.
python3 scripts/v031.py build
python3 scripts/v031.py audit
```

Los recursos y entregables se escriben en `renders/v03_1/`. El reel confronta las dos caras de cada corte con 23 fotogramas por lado. La comparativa presenta V03 a la izquierda y V03.1 a la derecha. Sus dos pistas seleccionables corresponden a cada versión. La hoja de contacto muestra el inicio, centro y fin de cada lado, incluidos los cuadros consecutivos del empalme.

La validación exige decodificación completa, cadencia constante, identidad de los paquetes de imagen de la conversación y los tres primeros bloopers, conservación del PCM del diálogo, y coincidencia de los 46 cuadros de cada límite con los componentes de origen a resolución de control. Los informes y muestras que contienen estudiantes se conservan en la entrega privada.

## Cierre definitivo de la misma versión

Con los dos másteres aprobados y el PNG institucional en su carpeta local, ejecutar desde la raíz:

```bash
python3 scripts/cierre_v031.py
python3 scripts/cierre_v031_qa.py
```

La EDL final se deriva de la EDL efectiva aprobada. Retira los 312 cuadros de `extra-cierre` y adelanta el agradecimiento 10,4 segundos. El SRT pasa de 143 a 140 bloques. El escudo RGBA de 2000 × 2000 se compone a 176 × 176 en la esquina superior derecha de la apertura y el agradecimiento. El montaje utiliza copia directa del tramo central de ambos másteres. Los fragmentos que requieren codificación en los límites de grupo de imágenes usan H.264 sin pérdida. El audio parte de la mezcla PCM aprobada, con un único corte a nivel de muestra.

La entrega definitiva se guarda en `renders/v03_1/definitivo/`. Las dos capturas de la galería de cierre omiten las identidades de los alumnos.

### Resultados de la entrega definitiva

Los dos másteres pasaron la decodificación completa a 1920 × 1080 y 30 fps. Duración de 12:03.933, con 21.718 cuadros por máster. El cotejo de imagen coincidió con los cuadros retenidos de cada referencia, excluyendo únicamente el rectángulo del escudo durante la apertura y el agradecimiento. El detector de negro no registró intervalos accidentales.

La mezcla final mide −16,33 LUFS y −1,65 dBTP. El PCM previo a la codificación coincide muestra por muestra con los dos tramos de la mezcla aprobada. Ambos MP4 contienen la misma señal AAC decodificada. Los 140 bloques retenidos del SRT conservan texto y tiempos. Se comprobó en imagen el subtítulo del saludo a los 21 segundos y el plano correspondiente del máster limpio.
