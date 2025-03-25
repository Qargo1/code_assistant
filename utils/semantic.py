from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance, 
    VectorParams, 
    PointStruct, 
    Filter, 
    FieldCondition, 
    MatchText
)
from ollama import embed
import os
import textwrap
import re
import hashlib
from functools import lru_cache

OLLAMA_EMBED = "nomic-embed-text"
CHUNK_SIZE = 1000
QDRANT_CONFIG = {
    "optimizers_config": {
        "indexing_threshold": 10000,
        "memmap_threshold": 20000
    },
    "hnsw_config": {
        "m": 32,
        "ef_construct": 200
    }
}
QDRANT_PATH = "qdrant_storage"

class QdrantCodeSearch:
    def __init__(self, merged_file="merged_code.txt"):
        self.client = QdrantClient(path=QDRANT_PATH)
        self.merged_file = merged_file
        self.collection_name = "code_search"
        self.model_map = {
            'cs': 'nomic-embed-text', #'codebert-csharp',
            'xaml': 'nomic-embed-text', #'xaml-embedder',
            'default': 'nomic-embed-text'
        }
        self._init_collection()

    def _init_collection(self):
        test_embed = self._get_cached_embed("test", "default")
        self.vector_size = len(test_embed)
        
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE
            ),
            **QDRANT_CONFIG
        )

    @lru_cache(maxsize=5000)
    def _get_cached_embed(self, text, lang):
        model = self.model_map.get(lang, self.model_map['default'])
        try:
            response = embed(model=model, input=text)
            if 'embeddings' not in response:
                raise ValueError(f"Model {model} did not return embeddings: {response}")
            embeddings = response['embeddings']
            if not embeddings:
                raise ValueError(f"No embeddings returned for model {model}")
            return embeddings[0]
        except Exception as e:
            print(f"Error getting embedding for model {model}: {str(e)}")
            raise

    def _semantic_chunker(self, text):
        lines = text.split('\n')
        chunks = []
        current_chunk_lines = []
        start_line = 0
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if re.match(r'^\s*(namespace|class|interface|void|public|private|protected|{|}|<[^>]+>|<!--|//)', stripped_line):
                if current_chunk_lines:
                    chunk_text = '\n'.join(current_chunk_lines)
                    chunks.append({
                        'text': chunk_text,
                        'start_line': start_line + 1,
                        'end_line': i
                    })
                current_chunk_lines = [line]
                start_line = i
            else:
                current_chunk_lines.append(line)
        if current_chunk_lines:
            chunk_text = '\n'.join(current_chunk_lines)
            chunks.append({
                'text': chunk_text,
                'start_line': start_line + 1,
                'end_line': len(lines)
            })
        return chunks

    def load_and_index_data(self):
        if not os.path.exists(self.merged_file):
            raise FileNotFoundError(f"Merged file {self.merged_file} not found")

        with open(self.merged_file, 'r', encoding='utf-8') as f:
            content = f.read()

        chunks = self._semantic_chunker(content)
        points = []
        
        for idx, chunk in enumerate(chunks):
            lang = 'cs' if re.search(r'\b(class|namespace|void)\b', chunk['text']) else 'xaml'
            embedding = self._get_cached_embed(chunk['text'], lang)
            
            points.append(
                PointStruct(
                    id=idx,
                    vector=embedding,
                    payload={
                        "text": chunk['text'],
                        "source": self.merged_file,
                        "lang": lang,
                        "start_line": chunk['start_line'],
                        "end_line": chunk['end_line']
                    }
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def _hybrid_search(self, query, top_k=5, vector_weight=0.7):
        vector_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=self._get_cached_embed(query, "default"),
            limit=top_k*2
        )
        
        keyword_results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(
                    key="text",
                    match=MatchText(text=query))
                ]
            ),
            limit=top_k*2
        )[0]
        
        return self._rank_fusion(vector_results, keyword_results, vector_weight)

    def _rank_fusion(self, vector_res, keyword_res, weight):
        combined = {}
        for idx, hit in enumerate(vector_res):
            combined[hit.id] = combined.get(hit.id, 0) + (1 - idx*0.1)*weight
            
        for idx, hit in enumerate(keyword_res):
            combined[hit.id] = combined.get(hit.id, 0) + (1 - idx*0.1)*(1 - weight)
            
        return sorted(combined.items(), key=lambda x: x[1], reverse=True)[:3]

    def search_code(self, query, top_k=3):
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string in search_code")
        print(f"Query received: {query}, type: {type(query)}")
        results = self._hybrid_search(query, top_k)
        return [
            {
                "text": hit.payload["text"],
                "score": score,
                "source": hit.payload.get("source", ""),
                "lang": hit.payload.get("lang", "unknown")
            }
            for hit, score in results
        ]