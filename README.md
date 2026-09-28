# Lazy Obsidian

Tu bóveda de notas, consultable desde la terminal.

## Qué es

Una TUI para consultar tu Obsidian. Escribes una pregunta en una barra de búsqueda,
la app busca entre tus propias notas y te responde con lo que encontró.

## Por qué existe

Las notas están ahí, pero nunca las relees. Están acumuladas: recetas, ideas sueltas,
fragmentos de libros, decisiones que tomaste hace un año y ya no recuerdas por qué.

Los buscadores de internet no sirven para eso. Y un gestor de notas solo te deja
buscar palabras exactas, cuando lo que recordás es la idea, no la palabra.

Lazy Obsidian responde a eso: **preguntás en tus palabras y te devuelve tus notas.**

- *"¿qué era lo que quería hacer con el tema de las consultas SQL lentas?"*
- *"esa receta de pasta que anoté en algún lado"*

## Cómo se siente

Una sola pantalla de terminal, tres zonas:

- **Izquierda** — la conversación. Escribís, y las respuestas se acumulan ahí.
- **Derecha** — el árbol de archivos. Para cuando sabés dónde está la nota
  y solo querés abrirla.
- **Abajo** — la barra de búsqueda. El lugar donde ocurre la magia.

Sin navegador, sin copiar y pegar, sin pestañas. Todo en el mismo lugar.

## Para quién

Para alguien que ya usa Obsidian a diario y siente que lo tiene medio abandonado.
No es una app de notas nueva: es una forma mejor de *volver* a las que ya tenés.

## Estado del proyecto

En desarrollo. La indexación de las notas ya funciona; la parte de responder
preguntas está en camino.

## Empezar

Necesitas Python 3.13, [Ollama](https://ollama.com) corriendo en local y
`ollama pull nomic-embed-text`.

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
python main.py
```

## Licencia

A definir.
