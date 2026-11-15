# Creator Studio · MVP 0.1

Primer prototipo **real y ejecutable** del estudio audiovisual IA de UniFormer: proyectos, guiones, escenas, biblioteca de recursos, conexión opcional a proveedor compatible con OpenAI, búsqueda opcional de clips Pexels y exportación FFmpeg H.264/AAC.

> **ATENCIÓN:** aplicación **local de un solo usuario**. No incorpora login, cuotas, aislamiento entre clientes, antivirus de archivos, moderación ni límites de facturación. **No la expongas públicamente en Internet** ni aceptes usuarios externos antes de construir esas defensas. No se ha conectado ni verificado ninguna cuenta de IA, Pexels o redes sociales.

## Ejecutar

Necesitas Python 3.11+ y FFmpeg/ffprobe accesibles desde `PATH`.

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn studio.app:app --host 127.0.0.1 --port 8000
```

Abre **http://127.0.0.1:8000**. Se creará un proyecto de demostración que **sí puedes exportar en MP4** sin servicios adicionales. Los archivos se guardan en `data/` (excluido de Git).

## Activar IA real (opcional)

El servidor espera una URL HTTPS para un endpoint *chat completions* compatible con OpenAI. Configura variables de entorno **privadas**:

```bash
export AI_CHAT_URL="https://tu-proveedor.example/v1/chat/completions"
export AI_MODEL="modelo-verificado"
export AI_API_KEY="clave-privada"
```

La aplicación **no incluye proveedor, modelo ni clave predefinidos**; no garantiza compatibilidad hasta probar tu proveedor. Una vez configurado, el botón `Crear storyboard` envía la idea y guarda las escenas que realmente devuelve la IA. El modelo solo escribe un guion técnico; no genera vídeos, voces ni imágenes por sí mismo.

## Buscar clips (opcional)

```bash
export PEXELS_API_KEY="clave-de-tu-cuenta"
```

El apartado `Biblioteca visual` consulta `https://api.pexels.com/v1/videos/search`. Muestra autor y enlace al contenido original; **no descarga ni revende clips**. Antes de importar y utilizar material, comprueba derechos de uso, posibles derechos de imagen, marcas y reglas de la plataforma. [Documentación de Pexels](https://www.pexels.com/api/documentation/) · [Licencia](https://www.pexels.com/license/).

## Qué funciona

- CRUD persistente de proyectos y escenas, cambio de formato, reordenación, notas y duraciones.
- Importar vídeos, imágenes y audios (máximo 200 MB por archivo), asignarlos a cada escena.
- Vista previa del storyboard y panel de línea de tiempo (sin previsualización sincronizada del montaje completo).
- Renderizar **MP4 real** (H.264/AAC) con FFmpeg, 24 FPS, dimensiones 720×1280 (vertical), 1280×720 (horizontal), 960×960 (cuadrado).
- Fondos tipográficos originales si una escena no tiene clip; clips ajustados al encuadre, pistas de voz importadas alineadas a la duración.
- Crear guiones con IA real cuando el proveedor haya sido configurado y verificado.
- Buscar Pexels cuando exista clave de API.
- Estados de render y enlace a descargar resultado.

## No implementado / siguientes fases

- Cuentas multiusuario, equipos, roles, facturación, límites y protección de archivos públicos.
- Generación nativa de vídeo e imagen por IA, TTS, SFX, música, mezcla inteligente, transiciones elaboradas, subtítulos sincronizados, edición multicapa en tiempo real.
- Publicación en TikTok, Instagram, YouTube, X/LinkedIn y sus permisos OAuth/API.
- Analíticas de redes, selección inteligente de miniaturas, calendario social, aprendizaje de resultados y automatización comercial.
- Render distribuido en GPU, colas persistentes, CDN, optimización de costes y registros de licencias.

## Tests

```bash
python -m pytest -q
```

## Seguridad y arquitectura

El backend FastAPI y SQLite son suficientes **solo para desarrollo local**. El servidor atiende una URL loopback para evitar exposición accidental. La aplicación no ofrece endpoints de descargar stock remoto para evitar almacenamiento masivo e incumplimientos de licencia. Los datos de API quedan en variables de entorno, nunca en el frontend. El proceso de render no ejecuta órdenes del usuario a través de un shell. El sistema de trabajos es temporal en memoria y desaparece al reiniciar.

Estructura:

```
studio/app.py         API, proyectos, recursos, IA, stock, trabajos
studio/renderer.py    Motor FFmpeg + gráficos originales Pillow
studio/web/           UI responsive
 tests/               Pruebas funcionales
```

## Licencia

Código de demostración. Antes de comercializarlo, decidir una licencia, completar seguridad y auditar dependencias y términos de cada proveedor externo.