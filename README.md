![Portada editorial de El túnel](docs/galeria-v03/apertura.jpg)

# EL TÚNEL · V03

Videopodcast de Literatura del Colegio Humboldt Caracas sobre la violencia de género en la novela de Ernesto Sabato. **Cuando el control se disfraza de amor.** La edición conserva la conversación aprobada e incorpora capítulos, cápsulas de lectura, identificación institucional y un cierre renovado.

![Versión V03](https://img.shields.io/badge/versi%C3%B3n-V03-8c4f42)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab)
![FFmpeg](https://img.shields.io/badge/FFmpeg-libx264%20%2F%20libass-168446)
![Resolución 1920×1080](https://img.shields.io/badge/resoluci%C3%B3n-1920%C3%971080-353740)
![30 fps](https://img.shields.io/badge/fps-30-353740)
![Auditoría local](https://img.shields.io/badge/auditor%C3%ADa-local-5f6368)
![Entrega local](https://img.shields.io/badge/estado-entrega%20local-8c4f42)

La [auditoría audiovisual](docs/V03_AUDITORIA_AUDIOVISUAL.md) y la [EDL](docs/V03_EDL.md) documentan el conformado de 12:10.433. La prueba semestral I se evalúa en cuatro ejes. La [matriz](docs/V03_MATRIZ_RUBRICA.md) vincula los doce criterios con intervenciones y tiempos V03, diferencia cita, paráfrasis e interpretación y registra los límites del cotejo.

| Eje | Indicadores |
|---|---|
| Análisis literario | Manifestaciones de violencia, temas centrales y evidencia de la novela |
| Perspectiva crítica | Postura frente a la violencia, vínculo con la realidad y reflexión del espectador |
| Discurso audiovisual | Estructura, lenguaje y ritmo |
| Producción | Audio, video y uso de los recursos audiovisuales |

## Galería

La galería muestra arte editorial creado para el proyecto. Las muestras de cierre y bloopers se generaron sin nombres ni retratos.

| | |
|---|---|
| ![Capítulo I](docs/galeria-v03/capitulo-1.jpg) | ![Capítulo II](docs/galeria-v03/capitulo-2.jpg) |
| ![Capítulo III](docs/galeria-v03/capitulo-3.jpg) | ![Capítulo IV](docs/galeria-v03/capitulo-4.jpg) |
| ![Mapa de la obsesión](docs/galeria-v03/mapa.jpg) | ![Perspectiva del narrador](docs/galeria-v03/perspectiva.jpg) |
| ![Bloopers](docs/galeria-v03/detras-de-camaras.jpg) | ![Agradecimiento](docs/galeria-v03/agradecimiento.jpg) |
| ![Miniatura editorial](docs/galeria-v03/miniatura.jpg) | ![Evidencia textual](docs/galeria-v03/evidencia.jpg) |

![Fotogramas sucesivos de la animación del capítulo III](docs/galeria-v03/motion.jpg)

## Arquitectura

**Flujo audiovisual**

```mermaid
flowchart LR
  A[Unidades de video V02] --> D[Conformado V03]
  B[Cortinas y cápsulas] --> D
  C[Mezcla y reparación localizada] --> D
  D --> E[Máster limpio]
  E --> F[Máster subtitulado]
```

**Renderizado**

```mermaid
flowchart LR
  A[Fotogramas Pillow] --> B[Muestras]
  B --> C[Codificación de cortinas]
  C --> D[Ensamblaje FFmpeg]
  E[Caché V02] --> D
  D --> F[Dos archivos MP4]
```

**Control de calidad**

```mermaid
flowchart LR
  A[EDL V02 y V03] --> B[Comparación de fuentes e intervalos]
  C[Másteres y SRT] --> D[Decodificación y cotejo]
  B --> E[Informe de conservación]
  D --> F[Auditoría técnica]
  G[Diálogo y fuentes] --> H[Matriz académica]
```

**Configuración y generación**

```mermaid
flowchart LR
  A[Configuraciones V02 y V03] --> D[EDL V03]
  B[Identidad local y recurso institucional] --> E[Gráfica y caché]
  D --> E
  D --> F[SRT conformado]
  C[SRT revisado de V02] --> F
```

## Reproducción y versiones

La [guía V03](docs/v03.md) detalla dependencias, archivos locales requeridos, configuración, render, subtitulado, auditoría y derechos. El recorrido técnico pasa por `edl`, `preview`, `build` y `audit` en `scripts/v03.py`.

- **V01** · Primer montaje y candidato audiovisual. [Producción](docs/produccion.md).
- **V02** · Recuperación del diálogo grupal y consolidación de la identidad de carboncillo. [Referencia V02](docs/v02.md).
- **V03** · Identidad institucional en texto, revisión pedagógica y cierre editorial.

## Disponibilidad

El máster subtitulado, el limpio, el SRT, la miniatura, las cortinas y las hojas de contacto están en `renders/v03/` del entorno de producción. La publicación del video y sus materiales identificables queda sujeta a autorización.
