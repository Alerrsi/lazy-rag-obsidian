from langchain_community.document_loaders import ObsidianLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader



class VectorialTrasnfer():
    OBSIDIAN_PATH = "/home/alerrsi/Documents/Obsidian/obsidian-notes"
    DATABASE = "../App/DB"


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

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    
        self.vectorstore = Chroma.from_documents(
            documents=splits, 
            embedding=embeddings, 
            persist_directory=self.DATABASE,
            collection_name="notas"
        )

    
    def add():
        pass


