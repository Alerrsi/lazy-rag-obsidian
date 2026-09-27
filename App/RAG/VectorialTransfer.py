import hashlib

from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.document_loaders.text import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma





class VectorialTransfer():
    OBSIDIAN_PATH = "/home/alerrsi/Documents/Obsidian/"
    DATABASE = "./App/DB/Chroma/"



    def __get_ids(self, chunks) -> list:

        return [
            hashlib.sha256(chunk.page_content.encode()).hexdigest()
            for chunk in chunks
        ]



    def load(self) -> None:

        embedding = OllamaEmbeddings(model="nomic-embed-text")

        loader = DirectoryLoader(
            loader_cls=UnstructuredMarkdownLoader,
            path=self.OBSIDIAN_PATH,
            glob="**/*.md"
        )

        docs = loader.load()

        # definimos la cantidad de caracteres por chunk que son 1000
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        # Aplicamos la división a los documentos
        splits = text_splitter.split_documents(docs)

        ids = self.__get_ids(splits)

        self.vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embedding,
            persist_directory=self.DATABASE,
            collection_name="Notas",
            collection_metadata={'hnsw:space': 'cosine'}
        )
