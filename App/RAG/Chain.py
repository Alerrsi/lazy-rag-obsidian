import dotenv
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI

from .VectorialTransfer import VectorialTransfer


dotenv.load_dotenv()

RETRIEVER_K = 4


class Chain:
    """Pregunta -> recuperacion -> Gemini. El indice se abre, no se rehace."""

    plantilla = """
    Como modelo respondes solamente basandote en el contexto dado.
    Si algo no coincide con el contexto, o no aparece, deci explicitamente que
    la informacion no se encuentra en las notas de la boveda. No completes con
    lo que sepas por fuera.
    Responde en el idioma de la pregunta.
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
        self.modelo = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        self._retriever = None

    def search(self, question: str) -> str:
        if self._retriever is None:
            # get_vectorstore() es idempotente: la primera vez sincroniza lo
            # que falte, despues solo devuelve el handle. Antes esto llamaba a
            # load(), que reindexaba la boveda completa en cada pregunta.
            self._retriever = self.transfer.get_vectorstore().as_retriever(
                search_kwargs={"k": RETRIEVER_K}
            )

        chain = (
            {
                "context": self._retriever | self._formatter,
                "question": RunnablePassthrough(),
            }
            | self.prompt
            | self.modelo
            | StrOutputParser()
        )

        return chain.invoke(question)

    def use_vault(self, path: str) -> None:
        """Cambia la boveda y tira el retriever cacheado."""
        self.transfer.update_path(path)
        self._retriever = None

    def _formatter(self, docs: list[Document]) -> str:
        if not docs:
            return "(ningun fragmento de tus notas coincide con la pregunta)"
        bloques = []
        for doc in docs:
            nota = doc.metadata.get("note") or doc.metadata.get("source", "?")
            bloques.append(f"### Nota: {nota}\n{doc.page_content}")
        return "\n\n".join(bloques)
