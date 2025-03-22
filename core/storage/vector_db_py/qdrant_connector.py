from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import logging
from typing import List, Dict, Optional
import yaml
import hashlib

class VectorSearchEngine:
    def __init__(self):
        self.client = None
        self.embedder = None
        self.collection_name = "code_vectors"
        self.logger = logging.getLogger(__name__)
        self._init_client()

    def _init_client(self):
        """Инициализация подключения из конфига"""
        with open("config/base_config.yaml") as f:
            config = yaml.safe_load(f)['vector_db']['qdrant']

        self.client = QdrantClient(
            host=config['host'],
            port=config['port'],
            api_key=config.get('api_key'),
            prefer_grpc=True
        )
        
        self._create_collection()

    def _create_collection(self):
        """Создание коллекции при инициализации"""
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=384,  # Для all-MiniLM-L6-v2
                    distance=Distance.COSINE
                )
            )
            self.logger.info("Created new Qdrant collection")

    def init_embedder(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Инициализация модели эмбеддингов"""
        from sentence_transformers import SentenceTransformer
        self.embedder = SentenceTransformer(model_name)
        self.logger.info(f"Initialized embedder: {model_name}")

    def _generate_file_id(self, file_path: str) -> str:
        """Генерация уникального ID для файла"""
        return hashlib.sha256(file_path.encode()).hexdigest()

    def add_file(self, file_path: str, content: str, metadata: dict) -> bool:
        """Добавление файла в векторную БД"""
        if not self.embedder:
            raise ValueError("Embedder not initialized")
        
        try:
            # Генерация эмбеддинга
            vector = self.embedder.encode(content).tolist()
            
            # Создание точки данных
            point = PointStruct(
                id=self._generate_file_id(file_path),
                vector=vector,
                payload={
                    "file_path": file_path,
                    "content": content[:1000],  # Сохраняем сокращенный контент
                    **metadata
                }
            )
            
            # Сохранение в Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=[point]
            )
            return True
        except Exception as e:
            self.logger.error(f"Error adding file: {str(e)}")
            return False

    def search_files(self, query: str, top_k: int = 5) -> List[Dict]:
        """Поиск по векторной БД"""
        if not self.embedder:
            raise ValueError("Embedder not initialized")
        
        query_vector = self.embedder.encode(query).tolist()
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True
        )
        
        return [{
            "file_path": hit.payload['file_path'],
            "score": hit.score,
            "content": hit.payload.get('content', '')
        } for hit in results]
        
    @lru_cache(maxsize=1000)
    def encode_cached(self, text: str) -> list:
        return self.embedder.encode(text).tolist()

    def search_files(self, query: str):
        query_vector = self.encode_cached(query)
        # ... остальная логика ...

    # Использование асинхронного кэша
    async def get_cached_or_fetch(key: str, coro):
        if cached := cache.get(key):
            return cached
        result = await coro
        cache.set(key, result)
        return result