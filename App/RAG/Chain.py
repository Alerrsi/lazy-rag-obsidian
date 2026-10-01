import re
from typing import Iterator

import dotenv
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI

from .VectorialTransfer import VectorialTransfer


dotenv.load_dotenv()

RETRIEVER_K = 4

# Patrones comunes de saludos o cortesía que no requieren consultar la base de datos vectorial
GREETING_PATTERN = re.compile(
    r"^(hola|buen(os)?\s*(d[ií]as|tardes|noches)|hey|qu[eé]\s*tal|buenas|c[oó]mo\s*est[aá]s?|saludos)[\s\.,!\?]*$",
    re.IGNORECASE,
)


class Chain:
    """Pregunta -> recuperacion -> Gemini con streaming y bypass de saludos."""

    plantilla = """
    Como modelo respondes solamente basandote en el contexto dado.
    Si algo no coincide con el contexto, o no aparece, deci explicitamente que
    la informacion no se encuentra en las notas de la boveda. No completes con
    lo que sepas por fuera.
    Responde en el idioma de la pregunta.
    Debes tener en cuanta que si el usuario envia un mensaje que no tenga que ver con nada
    y solo es saludo, debes saludar, el trato con el usuario deber ser como amigo de confianza
    Al final, agregá una linea que diga "Fuentes:" y lista ahi el nombre de
    cada nota del contexto que hayas usado, con el formato
    - <nombre de la nota> — <que sacaste de ella>. No pongas numeros sueltos:
    escribí el nombre de la nota.

    Contexto:
    {context}

    Pregunta:
    {question}

    Respuesta:
    """
    prompt = ChatPromptTemplate.from_template(plantilla)

    def __init__(self) -> None:
        self.transfer = VectorialTransfer()
        self.modelo = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.2,
        )
        self._retriever = None

    def _get_retriever(self):
        if self._retriever is None:
            self._retriever = self.transfer.get_vectorstore().as_retriever(
                search_kwargs={"k": RETRIEVER_K}
            )
        return self._retriever

    def stream_search(self, question: str) -> Iterator[str]:
        """Transmite tokens generados por el LLM en tiempo real (streaming)."""
        clean_q = question.strip()
        # Fast path: Saludos conversacionales sin inferencia RAG pesada
        if GREETING_PATTERN.match(clean_q):
            yield "¡Hola! ¿Cómo estás? ¿En qué puedo ayudarte hoy con tus notas?"
            return

        retriever = self._get_retriever()
        chain = (
            {
                "context": retriever | self._formatter,
                "question": RunnablePassthrough(),
            }
            | self.prompt
            | self.modelo
            | StrOutputParser()
        )

        for chunk in chain.stream(question):
            yield chunk

    def search(self, question: str) -> str:
        """Versión sincrónica que acumula el stream completo."""
        return "".join(self.stream_search(question))

    def use_vault(self, path: str) -> None:
        """Cambia la boveda y tira el retriever cacheado."""
        self.transfer.update_path(path)
        self._retriever = None

    def _formatter(self, docs: list[Document]) -> str:
        if not docs:
            return "(ningun fragmento de tus notas coincide con la pregunta)"

        partes = []
        for doc in docs:
            partes.append(
                f"---\nNota: {doc.metadata.get('note', doc.metadata.get('source', ''))}\n"
                f"{doc.page_content.strip()}"
            )
        return "\n\n".join(partes)
