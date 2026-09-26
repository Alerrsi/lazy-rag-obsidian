from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import ObsidianLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma





class VectorialTrasnfer():
    OBSIDIAN_PATH = "/home/alerrsi/Documents/Obsidian/"
    DATABASE = "./App/DB/Chroma/"


    def __init__(self):

        self.loader = DirectoryLoader(
            loader_cls=UnstructuredMarkdownLoader,
            path=self.OBSIDIAN_PATH,
            glob="**/*.md"
        )


        docs = self.loader.load()

        # definimos la cantidad de caracteres por chunk que son 1000
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        # Aplicamos la división a los documentos
        splits = self.text_splitter.split_documents(docs)


        for i in splits:
            print("Split 1")
            print(i)

        print(splits)

        embedding = OllamaEmbeddings(model="nomic-embed-text")


        self.vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embedding,
            persist_directory=self.DATABASE,
            collection_name="Notas",
            collection_metadata={'hnsw:space': 'cosine'}
        )



    def add():
        pass



vector = VectorialTrasnfer()
