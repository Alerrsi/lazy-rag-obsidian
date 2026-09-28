import hashlib
import json
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .Embeddings import OllamaEmbeddings


# chromadb construye su cliente global con un dict sin lock: dos hilos que
# abran el store al mismo tiempo revientan con KeyError o con errores raros de
# RustBindingsAPI. La app abre el indice en background mientras el usuario
# escribe, asi que el acceso se serializa con este lock.
CHROMA_LOCK = threading.RLock()


# Sube este numero cuando cambie el contrato de embeddings (modelo, prefijos,
# chunking). Fuerza un reindexado limpio en vez de mezclar vectores viejos
# incompatibles con los nuevos.
INDEX_SCHEMA_VERSION = 3

EMBEDDING_MODEL = "nomic-embed-text"
COLLECTION_NAME = "Notas"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


@dataclass
class IndexStats:
    """Que toco el ultimo _sync_index, para poder contarselo al usuario."""

    added_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)
    chunks_written: int = 0
    rebuilt: bool = False

    @property
    def changed_files(self) -> int:
        return len(self.added_files) + len(self.modified_files) + len(self.removed_files)


class VectorialTransfer():
    OBSIDIAN_PATH = "/home/alerrsi/Documents/Obsidian/"
    DATABASE = "./App/DB/Chroma/"

    def __init__(self, obsidian_path: str = None) -> None:
        if obsidian_path is not None:
            self.OBSIDIAN_PATH = obsidian_path
        self._embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            add_start_index=True,
        )
        self._vectorstore: Chroma | None = None
        self._indexed_vault: str | None = None
        self._stats = IndexStats()

    @classmethod
    def set_obsidian_path(cls, path: str) -> None:
        cls.OBSIDIAN_PATH = path

    def update_path(self, path: str) -> None:
        VectorialTransfer.OBSIDIAN_PATH = path
        self.OBSIDIAN_PATH = path
        self._vectorstore = None
        self._indexed_vault = None

    @property
    def stats(self) -> IndexStats:
        return self._stats

    def get_vectorstore(self) -> Chroma:
        """Vectorstore listo para consultar.

        Abrir el indice NO vuelve a embeber nada: solo sincroniza lo que
        faltaba. Es la unica puerta de entrada de la app.
        """
        with CHROMA_LOCK:
            if (
                self._vectorstore is not None
                and self._indexed_vault == self.OBSIDIAN_PATH
            ):
                return self._vectorstore

            self._vectorstore = self._open()
            return self._vectorstore

    def load(self) -> Chroma:
        """Alias viejo de get_vectorstore()."""
        return self.get_vectorstore()

    def reset_index(self) -> None:
        """Borra el indice persistido. La proxima get_vectorstore() reindexa."""
        self._vectorstore = None
        self._indexed_vault = None
        self._manifest_path.unlink(missing_ok=True)
        shutil.rmtree(self.DATABASE, ignore_errors=True)

    # --- apertura -----------------------------------------------------------

    def _open(self) -> Chroma:
        root = Path(self.OBSIDIAN_PATH).expanduser()
        if not root.is_dir():
            raise FileNotFoundError(f"No existe el directorio de fuentes: {root}")
        self.OBSIDIAN_PATH = str(root)

        store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=self._embeddings,
            persist_directory=self.DATABASE,
            collection_metadata={"hnsw:space": "cosine"},
        )
        self._stats = self._sync_index(store)
        self._indexed_vault = self.OBSIDIAN_PATH
        return store

    # --- sincronizacion incremental ----------------------------------------

    def _sync_index(self, store: Chroma) -> IndexStats:
        stats = IndexStats()
        files = self._scan_vault()
        manifest = self._read_manifest()

        if not self._manifest_matches_contract(manifest):
            self._clear_collection(store)
            manifest = self._empty_manifest()
            stats.rebuilt = True

        indexed = manifest["files"]
        added = sorted(p for p in files if p not in indexed)
        modified = sorted(p for p in files if p in indexed and indexed[p] != files[p])
        removed = sorted(p for p in indexed if p not in files)

        # Primero se borra lo que cambio o desaparecio, asi los chunks viejos de
        # esos archivos no sobreviven al reindexado parcial.
        for source in [*modified, *removed]:
            self._delete_source(store, source)

        docs = self._load_and_split(
            [Path(p) for p in (*added, *modified)], root_of=Path(self.OBSIDIAN_PATH)
        )
        if docs:
            store.add_documents(
                documents=docs,
                ids=[self._chunk_id(doc) for doc in docs],
            )
            stats.chunks_written = len(docs)

        stats.added_files = [self._display(p) for p in added]
        stats.modified_files = [self._display(p) for p in modified]
        stats.removed_files = [self._display(p) for p in removed]

        self._write_manifest(files)
        return stats

    def _manifest_matches_contract(self, manifest: dict) -> bool:
        return (
            manifest.get("schema_version") == INDEX_SCHEMA_VERSION
            and manifest.get("embedding_model") == EMBEDDING_MODEL
            and isinstance(manifest.get("files"), dict)
        )

    def _empty_manifest(self) -> dict:
        return {
            "schema_version": INDEX_SCHEMA_VERSION,
            "embedding_model": EMBEDDING_MODEL,
            "files": {},
        }

    @property
    def _manifest_path(self) -> Path:
        return Path(self.DATABASE) / "index_manifest.json"

    def _read_manifest(self) -> dict:
        try:
            return json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write_manifest(self, files: dict) -> None:
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._empty_manifest()
        payload["files"] = files
        self._manifest_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _scan_vault(self) -> dict:
        """{ruta absoluta: [mtime, size]} de los .md visibles de la boveda."""
        root = Path(self.OBSIDIAN_PATH)
        found: dict = {}
        for path in root.rglob("*.md"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            # Mismo criterio que usaba DirectoryLoader: nada de .git/.obsidian.
            if any(part.startswith(".") for part in relative.parts):
                continue
            stat = path.stat()
            found[str(path)] = [stat.st_mtime, stat.st_size]
        return found

    # --- carga y chunking ---------------------------------------------------

    def _load_and_split(self, paths: list[Path], root_of: Path) -> list[Document]:
        if not paths:
            return []

        def read(path: Path) -> str | None:
            try:
                return path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return None

        with ThreadPoolExecutor(max_workers=8) as pool:
            contents = list(pool.map(read, paths))

        docs: list[Document] = []
        for path, text in zip(paths, contents):
            if not text or not text.strip():
                continue
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": str(path),
                        "note": str(path.relative_to(root_of)),
                        "title": path.stem,
                    },
                )
            )
        return self._splitter.split_documents(docs)

    def _chunk_id(self, doc: Document) -> str:
        """Id estable por (archivo, contenido).

        Es lo que hacia falta antes: los ids se calculaban y se descartaban, asi
        que Chroma inventaba un UUID nuevo en cada indexado y la coleccion
        crecia sin limite con duplicados. Con este id, reindexar es un upsert.
        """
        material = f"{doc.metadata['source']}\x00{doc.page_content}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]

    def _delete_source(self, store: Chroma, source: str) -> None:
        try:
            store.delete(where={"source": source})
        except Exception:
            # Un filtro que no matchea nada no es un error que deba frenar la app.
            pass

    def _clear_collection(self, store: Chroma) -> None:
        ids = store.get(include=[])["ids"]
        for start in range(0, len(ids), 500):
            store.delete(ids=ids[start : start + 500])

    def _display(self, path: str) -> str:
        try:
            return str(Path(path).relative_to(Path(self.OBSIDIAN_PATH)))
        except ValueError:
            return path
