# Por qué la app era lenta, y qué se cambió

Documento de referencia del trabajo de performance sobre Lazy Obsidian.
Todas las cifras salen de medir esta bóveda real (`/home/alerrsi/Documents/Obsidian/`,
20 archivos `.md`, 612 KB, 27 fragmentos).

---

## Diagnóstico

### El problema de raíz

`Chain.search()` llamaba a `self.transfer.load()` **dentro del camino de la
consulta** (`App/RAG/Chain.py:36` en la versión anterior). Eso significaba que
cada pregunta que escribías reindexaba la bóveda entera de cero:

| Paso | Tiempo medido |
|---|---|
| `DirectoryLoader.load()` — releer los 20 `.md` | 2.10 s |
| `embed_documents(27)` — re-embeber los 27 fragmentos vía Ollama | 8.95 s |
| **Total antes de llamar a Gemini** | **≈ 11 s** |

Y lo peor: es lineal con el tamaño de la bóveda. Una bóveda 10 veces más grande
sonaba ~110 s por pregunta.

### Los otros problemas que arrastraba

1. **Los embeddings nunca se reutilizaban.** En todo el proyecto no existía
   ninguna llamada del tipo `Chroma(...)` (el constructor que *abre* un índice);
   solo `Chroma.from_documents(...)` (que *agrega*). Los vectores ya estaban
   guardados en `chroma.sqlite3` y nadie los leía nunca.

2. **`ids` se calculaban y se tiraban a la basura.** El código armaba los hashes
   sha256 y después no los pasaba a `from_documents`, así que Chroma inventaba un
   UUID aleatorio en cada indexado. Medido en la base: **324 filas para 27
   documentos distintos = 12 indexaciones acumuladas**. Cada pregunta sumaba 27
   vectores duplicados más, y el índice HNSW se re-sincronizaba cada vez.

3. **La TUI se congelaba.** `self.chain.search(text)` se llamaba directo dentro
   del handler de `Input.Submitted`, o sea en el event loop de Textual. Mientras
   corría, la app entera no repintaba ni respondía `ctrl+c`.

4. **`set_loading()` estaba roto.** Buscaba `#chat-input`, un widget que no
   existe en `ChatView` (el input real es `#message`, dentro de `SearchBarView`).
   Cada llamada moría con `NoMatches`. Nunca se usó, así que el bug quedó
   escondido.

5. **`UnstructuredMarkdownLoader` para markdown plano.** Es un partitioner
   estructurado con NLTK, single-threaded, para archivos que son texto plano.
   Además arrastraba `unstructured`, `nltk`, `spacy`, `torch` y `onnxruntime`.

6. **Imports muertos.** `main.py` importaba `Chroma` y `HuggingFaceEmbeddings`
   sin usarlos: **0.88 s** solo en esa cadena de import (onnxruntime + torch).

7. **Prefijos de tarea ausentes.** `nomic-embed-text` está entrenado con
   prefijos `search_document:` / `search_query:`. `OllamaEmbeddings` de
   langchain no los aplica.

---

## Los cambios

### `App/RAG/Embeddings.py` (nuevo)

Sustituye a `OllamaEmbeddings` de langchain por una implementación propia que
habla con el cliente de `ollama` directamente.

- **Batching real**: manda los textos en lotes de 64 en una sola request HTTP,
  en vez de una request por texto. 27 round-trips seriales pasan a ser 1.
- **Prefijos de tarea** aplicados según el modelo, con una tabla
  `TASK_PREFIXES` que se puede extender.

```python
response = self._client.embed(model=self.model, input=batch, truncate=True, keep_alive=self.keep_alive)
```

### `App/RAG/VectorialTransfer.py` (reescrito)

La idea central: **abrir el índice y construirlo son cosas distintas**, y solo
la segunda paga el costo de los embeddings.

- `get_vectorstore()` es la única puerta de entrada. Devuelve el handle cacheado
  si la bóveda no cambió; si cambió, sincroniza solo lo que falta.
- **Constructor `Chroma(...)` en vez de `from_documents(...)`**: abre el índice
  persistido sin re-embeber nada.
- **Indexación incremental con manifiesto.** `App/DB/Chroma/index_manifest.json`
  guarda `{ruta: [mtime, size]}` de cada archivo indexado. Al abrir se compara:
  - sin cambios → 0 embeddings
  - archivos nuevos/modificados → se borran sus fragmentos viejos por `source` y
    se re-embeben solo esos
  - archivos borrados → se borran sus fragmentos
- **`ids` reales y estables**: `sha256(source + contenido)[:32]`. Ahora sí se
  pasan a `add_documents`, así que reindexar es un **upsert** y no un duplicado.
- **`INDEX_SCHEMA_VERSION`**: subirlo fuerza un reindexado limpio. Subió a 3
  porque los 324 vectores que había estaban embebidos sin prefijos y mezclarlos
  con los nuevos habría empeorado la recuperación; la primera corrida los borra.
- **Lectura directa con `pathlib`** en vez de `DirectoryLoader` +
  `UnstructuredMarkdownLoader`, con pool de hilos. Se conserva la regla de
  `DirectoryLoader` de ignorar directorios ocultos (`.git`, `.obsidian`).
- **`CHROMA_LOCK`**: `chromadb.SharedSystemClient` construye su cliente global
  con un dict sin lock, así que dos hilos abriendo el store a la vez reventan con
  `KeyError` o con errores raros de `RustBindingsAPI`. Como la app ahora abre el
  índice en background mientras el usuario escribe, el acceso va serializado.
- `reset_index()` para rehacer todo a mano.

Metadata que ahora se guarda por fragmento: `source`, `note` (ruta relativa) y
`title`.

### `App/RAG/Chain.py`

- `search()` ya **no** llama a `load()`. Usa `get_vectorstore()` y cachea el
  retriever.
- `ChatGoogleGenerativeAI` pasa a construirse en `__init__` de la instancia en
  lugar de ser atributo de clase evaluado al importar.
- `_formatter` ahora arma el contexto con el nombre de la nota en cada bloque
  (`### Nota: RAG/SQlite/Configuración.md`) y el prompt pide una línea `Fuentes:`
  con el nombre de cada nota usada. Antes el modelo no tenía forma de saber de
  dónde sacaba nada.
- `use_vault(path)` para cambiar de bóveda y tirar el retriever cacheado.

### `App/UI/app.py`

- `@work(thread=True)` para la consulta: retrieval y Gemini corren en un hilo y
  la TUI sigue respondiendo. `exclusive=True` en el grupo `ask` cancela la
  pregunta anterior si mandás otra.
- `warm_worker` en `on_mount`: abre/sincroniza el índice en background al
  arrancar, así la primera pregunta no paga ese costo.
- `_set_busy()` deshabilita el input, muestra `⏳ Buscando en tus notas…` en el
  chat y pone `…` en el subtítulo de la barra.
- `_report_index()` avisa por chat lo que se indexó ("2 nuevas, 1 modificada"),
  para que la sincronización no sea invisible.
- Manejo de errores: si la consulta o el indexado fallan, se avisa en el chat y
  el input se desbloquea.

**Un bug que apareció durante las pruebas y quedó corregido:** el handler correcto no
es `on_work_state_changed` sino **`on_worker_state_changed`**. El mensaje es
`Worker.StateChanged` y lleva `namespace="worker"`, así que Textual construye el
nombre con el namespace entero. Con el nombre anterior el handler no se
disparaba nunca y el input se quedaba bloqueado para siempre.

### `App/UI/components/chat/ChatView.py`

- `set_loading()` (roto) reemplazado por `set_status()`, que muestra u oculta un
  `Static` de estado bajo el log.
- Se fue el `MessageSubmitted`, que se posteaba pero nadie escuchaba.

### `main.py`

Imports `Chroma` y `HuggingFaceEmbeddings` eliminados: no se usaban y costaban
0.88 s de arranque.

---

## Resultados medidos

### Antes → después

| Escenario | Antes | Ahora |
|---|---|---|
| Indexado completo (una vez) | 11.0 s | 11.7 s |
| **Pregunta, bóveda sin cambios** | **11.0 s** | **1.3 s** |
| **Reiniciar la app y preguntar** | **11.0 s** | **1.3 s** |
| Abrir el índice sin re-embeber | no existía | 0.01 s |
| Retrieval (k=4) | dentro de los 11 s | 0.04 s |
| Crecimiento de la base por pregunta | +27 filas | 0 |
| Arranque (imports) | 6.3 s + 0.9 s de imports muertos | 6.3 s |

El indexado completo no se aceleró a propósito: es un costo de una sola vez, y
se paga una única vez. Lo que importa es que **después de esa vez no se repite**.

### Sync incremental

```
estado inicial:        filas=37  docs_distintos=37
1 nota nueva:          0.78s  chunks=3   added=['__bench_tmp.md']
sin cambios:           0.01s  chunks=0
1 nota modificada:     0.87s  chunks=4   modified=['__bench_tmp.md']
1 nota borrada:        0.03s  removed=['__bench_tmp.md']
estado final:          filas=37  docs_distintos=37   <- la nota temporal se fue
```

Cero crecimiento neto. La base ya no se infla.

### Verificado

- `pyflakes` limpio en `App/` y `main.py`.
- Montaje de la TUI bajo `run_test()`: 19 widgets, sin errores.
- `set_status()` / `_set_busy()` ya no reventan.
- Pregunta respondsiendo, pregunta cancelada por otra, error de red, bóveda
  inexistente: los cuatro caminos reparten el estado bien y desbloquean el input.
- Índice abierto concurrentemente desde 3 hilos sin `KeyError` (con el lock).
- End-to-end contra Gemini real, con citas de fuentes nombradas.

---

## Dos aclaraciones honestas

### Los prefijos de tarea no eran la causa de las malas respuestas

Mi hipótesis inicial era que `nomic-embed-text` sin prefijos arruinaba el
retrieval. La medí y **era casi falsa** en la versión que tenés instalada. Con
documentos y consulta de prueba, la similitud coseno sale así:

| Configuración | Similitudes |
|---|---|
| Con prefijos correctos | 0.496 / 0.669 / 0.472 |
| Sin prefijos (antes) | 0.530 / 0.680 / 0.497 |
| Prefijo equivocado en documentos | 0.539 / 0.704 / 0.515 |

El ranking es idéntico en los tres casos. Las versiones recientes de
`nomic-embed-text` son mucho más tolerantes a los prefijos faltantes que la
original. **Mantuve el cambio igual** porque es el uso documentado y no cuesta
nada, pero no es lo que arreglaba las respuestas.

### La app diciendo "no se encuentra" no era un bug

Después de los cambios, `Chain.search("que notas tengo sobre SQL lento")` devuelve
*"La información no se encuentra en las notas de la bóveda"*. Lo revisé: la
recuperación funciona, el hit #1 es `RAG/SQlite/Configuración.md`, y **realmente
no hay nada sobre SQL lento en esta bóveda**. El ejemplo del README sobre
"consultas SQL lentas" es texto de marketing, no contenido real. El modelo
contestando eso está contestando bien.

---

## Deuda técnica que quedó (fuera del alcance de este trabajo)

- **`langchain_community.vectorstores.Chroma` está deprecado** desde LangChain
  0.2.9 y se va en 1.0. Con `langchain==1.3.11` instalado todavía funciona, pero
  va a romper. El reemplazo es el paquete `langchain-chroma`, que habría que
  agregar a `requirements.txt`.
- **`App/DB/main.py` está muerto**: crea un `PersistentClient` al importar y no
  lo importa nadie. Duplica lo que ahora hace `VectorialTransfer`. Habría que
  borrarlo.
- **`unstructured`, `nltk`, `spacy`, `torch` y `onnxruntime`** ya no se usan para
  leer archivos, pero siguen en `requirements.txt` (~2 GB). Se pueden quitar
  después de confirmar que nada más los importa.
- **El costal de embeddings de 8.95 s** es el cuello de botella real del primer
  indexado. Si una bóveda grande lo hace sentir, el camino es un modelo de
  embeddings local o una API remota, no más optimización de la app.
