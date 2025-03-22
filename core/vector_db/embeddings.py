import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict, Any, Optional, Tuple

class EmbeddingManager:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """Initialize the embedding manager with a specific model."""
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.id_to_data = {}  # Map IDs to original data
        self.next_id = 0
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def create_index(self, dimension: int, index_type: str = 'l2') -> None:
        """Create a new FAISS index."""
        try:
            if index_type == 'l2':
                self.index = faiss.IndexFlatL2(dimension)
            elif index_type == 'cosine':
                self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            else:
                raise ValueError(f"Unsupported index type: {index_type}")
            
            print(f"<self>Created {index_type} index with dimension {dimension}</self>")
            
        except Exception as e:
            print(f"<error>Failed to create index: {str(e)}</error>")
            raise

    def add_items(self, items: List[Dict[str, Any]]) -> List[int]:
        """Add items to the index."""
        try:
            # Extract text for embedding
            texts = [item['text'] for item in items]
            
            # Generate embeddings
            embeddings = self.model.encode(texts)
            
            if self.index is None:
                self.create_index(embeddings.shape[1])
            
            # Normalize for cosine similarity if using IP index
            if isinstance(self.index, faiss.IndexFlatIP):
                faiss.normalize_L2(embeddings)
            
            # Assign IDs and add to index
            ids = np.arange(self.next_id, self.next_id + len(items))
            self.index.add_with_ids(embeddings, ids)
            
            # Store original data
            for id_, item in zip(ids, items):
                self.id_to_data[int(id_)] = item
            
            self.next_id += len(items)
            print(f"<self>Added {len(items)} items to index</self>")
            
            return ids.tolist()
            
        except Exception as e:
            print(f"<error>Failed to add items: {str(e)}</error>")
            raise

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar items."""
        try:
            if self.index is None:
                raise ValueError("Index not initialized")
            
            # Generate query embedding
            query_vector = self.model.encode([query])[0].reshape(1, -1)
            
            # Normalize for cosine similarity if using IP index
            if isinstance(self.index, faiss.IndexFlatIP):
                faiss.normalize_L2(query_vector)
            
            # Search
            distances, indices = self.index.search(query_vector, k)
            
            # Format results
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx != -1:  # Valid index
                    item = self.id_to_data[int(idx)].copy()
                    item['score'] = float(1 / (1 + dist))  # Convert distance to similarity score
                    results.append(item)
            
            return results
            
        except Exception as e:
            print(f"<error>Search failed: {str(e)}</error>")
            raise

    def batch_search(self, queries: List[str], k: int = 5) -> List[List[Dict[str, Any]]]:
        """Perform batch search for multiple queries."""
        try:
            if self.index is None:
                raise ValueError("Index not initialized")
            
            # Generate query embeddings
            query_vectors = self.model.encode(queries)
            
            # Normalize for cosine similarity if using IP index
            if isinstance(self.index, faiss.IndexFlatIP):
                faiss.normalize_L2(query_vectors)
            
            # Batch search
            distances, indices = self.index.search(query_vectors, k)
            
            # Format results
            all_results = []
            for query_distances, query_indices in zip(distances, indices):
                query_results = []
                for dist, idx in zip(query_distances, query_indices):
                    if idx != -1:
                        item = self.id_to_data[int(idx)].copy()
                        item['score'] = float(1 / (1 + dist))
                        query_results.append(item)
                all_results.append(query_results)
            
            return all_results
            
        except Exception as e:
            print(f"<error>Batch search failed: {str(e)}</error>")
            raise

    def remove_items(self, ids: List[int]) -> None:
        """Remove items from the index."""
        try:
            if self.index is None:
                raise ValueError("Index not initialized")
            
            # Remove from FAISS index
            self.index.remove_ids(np.array(ids))
            
            # Remove from data map
            for id_ in ids:
                self.id_to_data.pop(id_, None)
            
            print(f"<self>Removed {len(ids)} items from index</self>")
            
        except Exception as e:
            print(f"<error>Failed to remove items: {str(e)}</error>")
            raise

    def save_index(self, path: str) -> None:
        """Save the FAISS index to disk."""
        try:
            if self.index is None:
                raise ValueError("Index not initialized")
            
            faiss.write_index(self.index, f"{path}.index")
            
            # Save mapping data
            np.save(f"{path}_mapping.npy", {
                'id_to_data': self.id_to_data,
                'next_id': self.next_id
            })
            
            print(f"<self>Saved index to {path}</self>")
            
        except Exception as e:
            print(f"<error>Failed to save index: {str(e)}</error>")
            raise

    def load_index(self, path: str) -> None:
        """Load a FAISS index from disk."""
        try:
            self.index = faiss.read_index(f"{path}.index")
            
            # Load mapping data
            data = np.load(f"{path}_mapping.npy", allow_pickle=True).item()
            self.id_to_data = data['id_to_data']
            self.next_id = data['next_id']
            
            print(f"<self>Loaded index from {path}</self>")
            
        except Exception as e:
            print(f"<error>Failed to load index: {str(e)}</error>")
            raise


class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
    
    def encode(self, text: str) -> np.ndarray:
        """Базовый интерфейс для эмбеддингов"""
        raise NotImplementedError

class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
    
    def encode(self, text: str) -> np.ndarray:
        return self.model.encode(text)