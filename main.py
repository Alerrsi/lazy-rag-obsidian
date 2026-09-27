from App.UI.app import Myapp
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


# run de TUI app
if __name__ == "__main__":
    app = Myapp()
    app.run()
