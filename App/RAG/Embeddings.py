import ollama
from langchain_core.embeddings import Embeddings


# nomic-embed-text exige prefijos de tarea: sin ellos el modelo mezcla el espacio
# de indexado con el de consulta y la recuperacion se vuelve casi aleatoria.
TASK_PREFIXES = {
    "nomic-embed-text": {
        "document": "search_document: ",
        "query": "search_query: ",
    },
}

DEFAULT_BATCH_SIZE = 64


class OllamaEmbeddings(Embeddings):
    """Embeddings contra Ollama local.

    Dos diferencias con langchain_community.OllamaEmbeddings que importan aca:

    - Habla con el cliente de `ollama` directamente y manda los textos en lotes
      (una request HTTP por lote) en vez de una request por texto. Indexar la
      boveda deja de ser N round-trips seriales.
    - Aplica el prefijo de tarea que pide el modelo. El wrapper de langchain no
      lo hace, y sin el las similitudes salen malas.
    """

    def __init__(
        self,
        model: str = "nomic-embed-text",
        batch_size: int = DEFAULT_BATCH_SIZE,
        base_url: str | None = None,
        keep_alive: str | None = "10m",
    ) -> None:
        self.model = model
        self.batch_size = max(1, batch_size)
        self.keep_alive = keep_alive
        self._client = ollama.Client(host=base_url) if base_url else ollama.Client()
        prefixes = TASK_PREFIXES.get(model, {})
        self._document_prefix = prefixes.get("document", "")
        self._query_prefix = prefixes.get("query", "")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed([self._document_prefix + text for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._embed([self._query_prefix + text])[0]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = self._client.embed(
                model=self.model,
                input=batch,
                truncate=True,
                keep_alive=self.keep_alive,
            )
            vectors.extend(response.embeddings)
        return vectors
