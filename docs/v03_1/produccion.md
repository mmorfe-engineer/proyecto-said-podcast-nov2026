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
