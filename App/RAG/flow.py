import os
import dotenv

from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from VectorialTransfer import VectorialTransfer


# cargar API KEY
dotenv.load_dotenv()



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

prompt = ChatPromptTemplate.from_template(plantilla)

# cargamos el modelo
modelo = ChatGoogleGenerativeAI(model="gemini-2.5-flash")


# Clase que almacena los elementos
transfer = VectorialTransfer()

transfer.load()


# buscador de elementos con un maximo de 4 concidencias
retriever = transfer.vectorstore.as_retriever(search_kwargs={"k": 4})

def formatter(docs : list[Document]) -> str :
    return "\n\n".join(doc.page_content for doc in docs)


# cadena final
chain =  (
    {
    "context": retriever | formatter,
    "question": RunnablePassthrough()
    } |
    prompt |
    modelo |
    StrOutputParser()
)


response = chain.invoke("Como se calcula el SoC de as baterias")

print(response)
