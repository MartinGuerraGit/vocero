# PRD MVP: Widget de Dictado Linux

## Objetivo

Construir un MVP de herramienta de dictado para Linux que funcione como widget
flotante y permita redactar texto para prompts de programación en cualquier
aplicación mediante inserción por portapapeles.

## Alcance Inicial

- Widget flotante visible sobre otras aplicaciones.
- Activación tipo push-to-talk mediante hotkey configurable.
- Captura de audio desde micrófono.
- Barra visual de nivel de sonido mientras el usuario dicta.
- Transcripción local/offline.
- Inserción por portapapeles, con fallback a copiado manual si el pegado automático falla.
- Foco en validar la experiencia de dictar prompts de programación, no en optimizar todavía la calidad semántica del prompt.

## Fuera de Alcance Inicial

- Transformación del dictado con LLM o mejora automática del prompt.
- Dependencias cloud obligatorias.
- Soporte multiplataforma.
- Migración a Rust en la primera versión.
- Inyección robusta de texto por APIs del sistema o simulación de teclado fuera del portapapeles.

## Decisiones Técnicas Iniciales

- Plataforma objetivo: Linux.
- Stack recomendado para MVP: Python + PySide6.
- Motor de transcripción: local/offline, preferentemente `faster-whisper` o alternativa compatible con Whisper.
- Inserción de texto: portapapeles como mecanismo principal.
- Hotkey global configurable con implementación best-effort en Linux.
- La futura migración a Rust queda registrada como dirección deseada si el MVP valida la UX.

## Riesgos Principales

- En Wayland, pegar automáticamente en cualquier aplicación puede ser inconsistente; el MVP debe tener fallback claro a copiado manual.
- En Wayland, capturar hotkeys globales también puede estar restringido por el compositor.
- La transcripción local puede requerir descargar modelos y elegir un tamaño que balancee precisión, latencia y consumo de CPU/RAM.
- Los permisos de micrófono y el stack de audio pueden variar entre distribuciones Linux.

## Criterio de Éxito del MVP

El usuario puede abrir un widget flotante, dictar una idea para un prompt de
programación, revisar el texto transcripto y llevarlo a otra aplicación usando
el portapapeles sin depender de servicios cloud.

## Dirección Futura

Si el MVP valida la experiencia, se evaluará migrar la aplicación a Rust para
mejorar distribución, consumo de recursos e integración con APIs de escritorio.
