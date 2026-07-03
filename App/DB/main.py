import chromadb




class VectorialDatabase():
    client = chromadb.PersistentClient(path='./App/DB/')

    def createCollection(self, name: str):
        collection = self.client.get_or_create_collection(
            name = name,
            metadata={'hnsw:space': 'cosine'}
        )
        return collection

db = VectorialDatabase()

db.createCollection("Notas")