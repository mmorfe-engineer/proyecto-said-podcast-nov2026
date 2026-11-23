# Bitácora de producción

## Versiones y recuperación

- V0 · Diagnóstico previo y ocho SRT privados. Commit inicial `e823304`.
- V1 · EDL con gancho separado, elipsis del falso arranque, cortes de capítulos y un cierre.
- V2 · Pruebas locales de apertura, gancho y transiciones. Los entregables de estas pruebas quedan en `renders/`.
- RC1 · Montaje con identidad institucional, cuatro bloopers, créditos genéricos y subtítulos. La versión de entrega definitiva depende de acreditar los nombres oficiales y cerrar la revisión de diálogo.

El archivo editable de cada decisión es `config/episodio.json`. El reel local de pruebas usa los mismos segmentos que el episodio. El caché conserva cada segmento validado para permitir cambios puntuales. Cada toma original se verifica con el archivo `work/rc/originales.sha256`. Las rutas privadas están excluidas de Git.

## Narrativa y acabado

Se mueve el gancho del clip 2 después de la apertura para fijar la pregunta central. Se elimina el ensayo largo del 1, se conserva la tesis del 3 y se recortan dos citas difíciles de confirmar. El capítulo del 6 conserva el desarrollo del argumento sobre la fiabilidad del narrador y su vuelta a la voz de María. El 7 aporta un agradecimiento y el 8 cierra con la pregunta. La cola incluye cuatro de seis tomas falsas. Las otras dos añaden una expresión dudosa o una conversación ajena al episodio y se descartan del montaje.

El tratamiento de imagen corrige contraste, exposición y saturación individualmente. La orientación se toma del original mediante FFmpeg. Los reencuadres en 2 y 3 son suaves; las tomas 5 y 6 se preservan en encuadre completo. El blooper vertical conserva su proporción sobre un fondo carbón. Se cubren dos empalmes de la presentación con un fotograma tratado en carboncillo, cuya salida anticipa el siguiente plano sobre voz en continuidad. Los capítulos II y IV usan escenas de la entrevista procesadas localmente como grabados. El motivo musical es original, generado como cuatro notas FM, textura y acorde grave.

El audio usa filtro paso alto, reducción moderada de ruido, compresión, ganancia por segmento y normalización de máster. El análisis de las muestras AAC decodificadas en coma flotante arroja picos superiores a 0 dBFS en los clips 3, 4 y 5 (aprox. +0.41, +0.21 y +0.97). Los episodios con varias muestras próximas al techo fueron aislados y breves. Ese dato por sí solo no prueba pérdida de señal original. La corrección entrega margen y evita atribuir recuperación a un proceso que no la demuestra. El canal derecho original mide entre 2.6 y 4.6 dB por encima del izquierdo en los ocho clips.

## Calidad y nomenclatura

La auditoría verifica por separado ambos MP4, incluyendo decodificación completa, geometría, frecuencia, cuadros respecto a la EDL, sonoridad, pico verdadero, negro y sincronización de tiempos de subtítulos. Genera fotogramas y una hoja de contacto privada en `work/rc/qa/`. El documento y los informes distinguen las pruebas objetivas de una revisión humana de texto, cortes y sonido.

Los subtítulos usan borradores de Whisper con revisión editorial, una segunda decodificación puntual y tiempos editables. Las acotaciones inciertas están en `work/rc/subtitulos_revision.json`. La división tipográfica y el tiempo asignado a cada subdivisión son automáticos dentro de cada intervención de origen. La transcripción de nombres propios de participantes se mantiene fuera de los recursos públicos. El archivo oficial de acreditación sigue pendiente.

## Resultado objetivo del RC1

Los másteres limpio y subtitulado duran 533.866667 segundos. Ambos se decodificaron
completos y contienen exactamente 16.016 cuadros con PTS y duración de cuadros
constantes a 30 fps. El audio AAC es idéntico entre las dos versiones. Se midieron
−16.03 LUFS integrados y −1.41 dBTP. El detector aplicado no encontró intervalos negros.
El SRT contiene 125 acotaciones sin solapamientos ni desbordamientos de tiempo.

La inspección de hojas de contacto comprobó las orientaciones, la composición de las
cortinas y la posición de los rótulos y subtítulos en los fotogramas muestreados.
Quedan cuatro pasajes señalados para cotejo a oído y acreditación nominal pendiente.
