import os
import dotenv

from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from .VectorialTransfer import VectorialTransfer


# cargar API KEY
dotenv.load_dotenv()

class Chain:
    plantilla = """
    Como modelo debes responder solamente basandote en el contexto dado,
    si hay algo que no coincide o no existe es tu deber decir que la información
    no se encuentra en tus fuentes de texto.
    Contexto:
    {context}

    Pregunta:
    {question}

    Respuesta:
    """
    transfer = VectorialTransfer()
    prompt = ChatPromptTemplate.from_template(plantilla)

    # cargamos el modelo
    modelo = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    def search(self, question: str) -> str:
        self.transfer.load()
        # buscador de elementos con un maximo de 4 concidencias
        retriever = self.transfer.vectorstore.as_retriever(search_kwargs={"k": 4})
        # cadena final
        chain =  (
            {
            "context": retriever | self._formatter,
            "question": RunnablePassthrough()
            } |
            self.prompt |
            self.modelo |
            StrOutputParser()
        )

        return chain.invoke(question)


    def _formatter(self, docs : list[Document]) -> str :
        return "\n\n".join(doc.page_content for doc in docs)
