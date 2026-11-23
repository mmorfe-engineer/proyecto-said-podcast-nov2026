# EDL V03

Los límites de programa se expresan a 30 fps. La salida es exclusiva. Las ventanas de origen mantienen la precisión de la EDL V02 y la duración de programa se conserva con el recuento de cuadros del conformado aprobado.

| Unidad | Entrada V03 | Salida V03 | Cuadros | Origen |
|---|---:|---:|---:|---|
| apertura | 00:00.000 | 00:17.000 | 510 | Gráfica |
| presentacion | 00:17.000 | 01:17.133 | 1804 | Video 1, 4.40–64.55 s |
| presentacion-continuacion | 01:17.133 | 01:37.933 | 624 | Video 1, 128.35–149.15 s |
| capitulo-1 | 01:37.933 | 01:45.933 | 240 | Gráfica |
| violencia | 01:45.933 | 02:52.067 | 1984 | Video 2, 0.45–66.58 s |
| anatomia | 02:52.067 | 03:12.067 | 600 | Gráfica |
| capitulo-2 | 03:12.067 | 03:20.067 | 240 | Gráfica |
| obsesion | 03:20.067 | 04:15.233 | 1655 | Video 3, 4.62–59.78 s |
| mapa | 04:15.233 | 04:28.233 | 390 | Gráfica |
| evidencia | 04:28.233 | 04:42.233 | 420 | Gráfica |
| capitulo-3 | 04:42.233 | 04:50.233 | 240 | Gráfica |
| postura | 04:50.233 | 05:30.900 | 1220 | Video 4, 3.15–43.82 s |
| acoso | 05:30.900 | 06:47.800 | 2307 | Video 5, 16.70–93.61 s |
| capitulo-4 | 06:47.800 | 06:55.800 | 240 | Gráfica |
| narrador | 06:55.800 | 09:17.067 | 4238 | Video 6, 0.00–141.25 s |
| perspectiva | 09:17.067 | 09:33.067 | 480 | Gráfica |
| despedidas | 09:33.067 | 10:24.333 | 1538 | Video 7, 5.63–56.90 s |
| epilogo | 10:24.333 | 10:34.333 | 300 | Gráfica |
| reflexion | 10:34.333 | 11:05.400 | 932 | Video 8, 7.82–38.88 s |
| creditos | 11:05.400 | 11:14.400 | 270 | Gráfica |
| detras-de-camaras | 11:14.400 | 11:21.600 | 216 | Gráfica |
| extra-reinicio | 11:21.600 | 11:32.533 | 328 | Blooper 3, 0.50–11.45 s |
| extra-pregunta | 11:32.533 | 11:46.133 | 408 | Blooper a, 4.90–18.50 s |
| extra-coro | 11:46.133 | 11:52.933 | 204 | Blooper b, 8.80–15.60 s |
| extra-cierre | 11:52.933 | 11:59.433 | 195 | Blooper c, 0.55–7.05 s |
| agradecimiento | 11:59.433 | 12:10.433 | 330 | Gráfica |

La EDL de máquina y la comparación de ventanas se generan en `renders/v03/edl.json` y `renders/v03/conservacion-edl.json`. Se conservaron nueve segmentos de diálogo de ocho archivos y cuatro bloopers. Se retiró `extra-espontaneo` (blooper 5, 10.15–23.65 s).
