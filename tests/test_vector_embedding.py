import unittest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from tools.vector_embedding_manager import EmbeddingManager, VectorCache, CodeEmbedder

class TestVectorEmbeddings(unittest.TestCase):
    """Тесты для работы с векторными эмбеддингами кода"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        # Создаем временную директорию для кэша
        self.temp_cache_dir = tempfile.mkdtemp()
        
        # Пример кода для тестирования
        self.test_csharp_code = """
        public class User 
        {
            public string Name { get; set; }
            
            public bool IsValid() 
            {
                return !string.IsNullOrEmpty(Name);
            }
        }
        """
        
        self.test_python_code = """
        class User:
            def __init__(self, name):
                self.name = name
                
            def is_valid(self):
                return self.name and len(self.name) > 0
        """
    
    def tearDown(self):
        """Очистка после завершения тестов"""
        if os.path.exists(self.temp_cache_dir):
            shutil.rmtree(self.temp_cache_dir)
    
    @patch('tools.vector_embedding_manager.ollama_embed')
    def test_vector_cache(self, mock_ollama_embed):
        """Тест кэширования векторных представлений"""
        # Настраиваем мок для ollama_embed
        mock_response = {"embeddings": [[0.1, 0.2, 0.3, 0.4]]}
        mock_ollama_embed.return_value = mock_response
        
        # Создаем кэш
        cache = VectorCache(self.temp_cache_dir)
        
        # Проверяем, что запрос отсутствует в кэше
        result = cache.get("test_key", "nomic-embed-text")
        self.assertIsNone(result)
        
        # Сохраняем вектор в кэш
        test_vector = [0.1, 0.2, 0.3, 0.4]
        cache.put("test_key", "nomic-embed-text", test_vector)
        
        # Проверяем, что вектор сохранен и может быть извлечен
        result = cache.get("test_key", "nomic-embed-text")
        self.assertEqual(result, test_vector)
        
        # Проверяем статистику кэша
        stats = cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
    
    @patch('tools.vector_embedding_manager.ollama_embed')
    def test_embedding_manager(self, mock_ollama_embed):
        """Тест менеджера эмбеддингов"""
        # Настраиваем мок для ollama_embed
        mock_ollama_embed.return_value = {"embeddings": [[0.1, 0.2, 0.3, 0.4]]}
        
        # Создаем менеджер эмбеддингов
        manager = EmbeddingManager(cache_dir=self.temp_cache_dir)
        
        # Получаем эмбеддинг
        embedding = manager.get_embedding("Test text", "nomic-embed-text")
        
        # Проверяем результат
        self.assertEqual(len(embedding), 4)
        self.assertEqual(embedding, [0.1, 0.2, 0.3, 0.4])
        
        # Запрашиваем тот же эмбеддинг еще раз (должен быть из кэша)
        embedding2 = manager.get_embedding("Test text", "nomic-embed-text")
        
        # Проверяем, что ollama_embed вызывался только один раз
        self.assertEqual(mock_ollama_embed.call_count, 1)
        
    @patch('tools.vector_embedding_manager.ollama_embed')
    def test_code_embedder(self, mock_ollama_embed):
        """Тест для эмбеддинга кода с учетом языка"""
        # Настраиваем мок для ollama_embed
        mock_ollama_embed.return_value = {"embeddings": [[0.1, 0.2, 0.3, 0.4]]}
        
        # Создаем embedder для кода
        manager = EmbeddingManager(cache_dir=self.temp_cache_dir)
        code_embedder = CodeEmbedder(manager)
        
        # Получаем эмбеддинги для разных языков
        csharp_embedding = code_embedder.embed_code(self.test_csharp_code, "csharp")
        python_embedding = code_embedder.embed_code(self.test_python_code, "python")
        
        # Оба должны использовать одну и ту же базовую модель в нашем моке
        self.assertEqual(csharp_embedding, [0.1, 0.2, 0.3, 0.4])
        self.assertEqual(python_embedding, [0.1, 0.2, 0.3, 0.4])
        
    @patch('tools.vector_embedding_manager.EmbeddingManager.get_embedding')
    def test_similarity_calculation(self, mock_get_embedding):
        """Тест расчета схожести между фрагментами кода"""
        # Настраиваем мок для get_embedding
        mock_get_embedding.side_effect = [
            [1.0, 0.0, 0.0, 0.0],  # Первый вызов
            [0.0, 1.0, 0.0, 0.0]   # Второй вызов
        ]
        
        manager = EmbeddingManager(cache_dir=self.temp_cache_dir)
        
        # Вычисляем схожесть между векторами
        similarity = manager.similarity("Code 1", "Code 2")
        
        # Для перпендикулярных векторов косинусное сходство должно быть 0
        self.assertEqual(similarity, 0.0)
        
        # Меняем поведение мока для тестирования схожих векторов
        mock_get_embedding.side_effect = [
            [1.0, 1.0, 1.0, 1.0],  # Третий вызов
            [1.0, 1.0, 1.0, 1.0]   # Четвертый вызов
        ]
        
        # Для идентичных векторов косинусное сходство должно быть 1
        similarity = manager.similarity("Same code", "Same code")
        self.assertEqual(similarity, 1.0)

if __name__ == '__main__':
    unittest.main() 