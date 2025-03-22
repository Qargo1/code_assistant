import json
from pathlib import Path
from transformers import pipeline
from typing import Dict, Any
import logging
from core.database.models import FileMetadata
from core.database.connection import get_session

logger = logging.getLogger(__name__)

class FileFilter:
    def __init__(self, model_name="google/flan-t5-base"):
        self.classifier = pipeline(
            "text2text-generation",
            model=model_name,
            device=0 if torch.cuda.is_available() else -1
        )
        self.cache = {}
        
        # Загрузка промпта
        with open("models/config/filter_prompt.json") as f:
            self.prompt_template = json.load(f)["prompt"]

    def _generate_prompt(self, file_content: str, question: str) -> str:
        return self.prompt_template.format(
            file_content=file_content[:2000],  # Ограничение контекста
            question=question
        )

    def check_relevance(self, file_path: Path, question: str) -> Dict[str, Any]:
        """Основной метод проверки релевантности файла"""
        try:
            if self._file_changed_since_last_analysis(file_path):
                self._force_reanalysis(file_path)
            # Проверка кэша
            cache_key = f"{file_path}-{question}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            # Чтение файла
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Генерация промпта
            prompt = self._generate_prompt(content, question)
            
            # Выполнение запроса к LLM
            result = self.classifier(
                prompt,
                max_length=200,
                num_return_sequences=1,
                temperature=0.3
            )
            
            # Парсинг результата
            response = json.loads(result[0]['generated_text'])
            
            # Обновление метаданных в БД
            self._update_metadata(file_path, response)
            
            # Кэширование
            self.cache[cache_key] = response
            return response
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return {"relevant": False, "confidence": 0.0, "error": str(e)}

    def _update_metadata(self, file_path: Path, response: dict):
        """Обновление метаданных файла в базе"""
        with get_session() as session:
            file_meta = session.query(FileMetadata).filter_by(
                file_path=str(file_path)
            ).first()
            
            if file_meta:
                file_meta.last_analyzed = datetime.now()
                file_meta.key_functions = response.get("keywords", [])
                session.commit()

    def batch_filter(self, files: list, question: str) -> list:
        """Пакетная обработка файлов"""
        return [self.check_relevance(Path(f), question) for f in files]