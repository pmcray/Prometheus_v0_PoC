import logging
import uuid
from typing import List, Dict, Any

from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

class MemoryAgent:
    """
    Manages the agent's memory using a vector store and text embeddings.
    """

    def __init__(self, collection_name: str = "prometheus_memory"):
        self.collection_name = collection_name

        # Initialize the embedding model
        # The model will be downloaded on first use
        self.embedding_model = TextEmbedding()
        logger.info("🧠 Initialized TextEmbedding model for MemoryAgent.")

        # Initialize Qdrant client for in-memory storage
        self.qdrant_client = QdrantClient(":memory:")
        logger.info("🧠 Initialized in-memory Qdrant client.")

        # Create the collection in Qdrant
        self._create_collection()

    def _create_collection(self):
        """
        Creates the collection in Qdrant to store the memory vectors.
        """
        try:
            self.qdrant_client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self._get_embedding_size(),
                    distance=models.Distance.COSINE
                ),
            )
            logger.info(f"✅ Collection '{self.collection_name}' created in Qdrant.")
        except Exception as e:
            logger.error(f"❌ Failed to create Qdrant collection: {e}")
            # This is a critical error, so we should probably raise it
            raise

    def _get_embedding_size(self) -> int:
        """
        Gets the embedding size of the model by embedding a dummy text.
        """
        dummy_text = "get embedding size"
        embedding = list(self.embedding_model.embed([dummy_text]))[0]
        return len(embedding)

    def add_to_memory(self, document: str, metadata: Dict[str, Any]):
        """
        Adds a document and its metadata to the memory.
        """
        try:
            # Generate a unique ID for the memory point
            point_id = str(uuid.uuid4())

            # Generate the embedding for the document
            embedding = list(self.embedding_model.embed([document]))[0]

            # Upsert the point into the Qdrant collection
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=embedding.tolist(), # Convert numpy array to list
                        payload={
                            "document": document,
                            **metadata
                        },
                    )
                ],
                wait=True,
            )
            logger.info(f"📝 Added document to memory with ID: {point_id}")
        except Exception as e:
            logger.error(f"❌ Failed to add document to memory: {e}")

    def retrieve_similar_failures(self, query: str, k: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieves the k most similar failures from memory based on a query.
        """
        try:
            # Generate the embedding for the query
            query_embedding = list(self.embedding_model.embed([query]))[0]

            # Search for similar points in the Qdrant collection
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=k,
                with_payload=True,
            )

            # Format the results
            results = []
            for hit in search_result:
                result = {
                    "score": hit.score,
                    "payload": hit.payload,
                }
                results.append(result)

            logger.info(f"🔍 Retrieved {len(results)} similar failures from memory.")
            return results
        except Exception as e:
            logger.error(f"❌ Failed to retrieve similar failures from memory: {e}")
            return []
