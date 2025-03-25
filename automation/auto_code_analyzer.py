"""
auto_code_analyzer.py - Автоматический анализатор кода

Модуль предоставляет автоматизированный анализ кода C# с использованием LLM.
Система способна самостоятельно искать нужные файлы, загружать их, анализировать
и выгружать из памяти, сохраняя результаты работы.
"""

import os
import re
import json
import time
import logging
import threading
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from queue import Queue, PriorityQueue
from functools import lru_cache
from datetime import datetime

# Импорт для работы с LLM
import ollama

# Импорт модулей проекта
from core.analysis.multilang_analyzer import MultiLanguageAnalyzer
from core.analysis.chunking import CodeChunker
from tools.large_csharp_analyzer import LargeCSharpAnalyzer
from utils.semantic import QdrantCodeSearch
from utils.db_manager import CodeKnowledgeDB

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/auto_analyzer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Константы
OLLAMA_MODEL = "qwen2.5-coder:3b"
MAX_MEMORY_DOCUMENTS = 10  # Максимальное количество документов в памяти
MAX_ITERATIONS = 5  # Максимальное количество итераций поиска
DB_PATH = "data/code_knowledge.db"

class AutoAnalysisTask:
    """Класс для представления задачи анализа"""
    
    def __init__(self, task_id: str, query: str, priority: int = 1):
        """
        Инициализация задачи анализа
        
        Args:
            task_id: Идентификатор задачи
            query: Запрос для анализа
            priority: Приоритет задачи (меньше = выше)
        """
        self.task_id = task_id
        self.query = query
        self.priority = priority
        self.status = "pending"
        self.result = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.iterations = 0
        self.memory = {}  # Память задачи
        self.loaded_documents = []  # Загруженные документы
        self.analysis_steps = []  # Шаги анализа
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование задачи в словарь"""
        return {
            "task_id": self.task_id,
            "query": self.query,
            "priority": self.priority,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "iterations": self.iterations,
            "memory": self.memory,
            "loaded_documents": self.loaded_documents,
            "analysis_steps": self.analysis_steps
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutoAnalysisTask':
        """Создание задачи из словаря"""
        task = cls(data["task_id"], data["query"], data["priority"])
        task.status = data["status"]
        task.result = data["result"]
        task.created_at = datetime.fromisoformat(data["created_at"])
        task.updated_at = datetime.fromisoformat(data["updated_at"])
        task.iterations = data["iterations"]
        task.memory = data["memory"]
        task.loaded_documents = data["loaded_documents"]
        task.analysis_steps = data["analysis_steps"]
        return task
    
    def add_step(self, action: str, content: str) -> None:
        """Добавление шага анализа"""
        self.analysis_steps.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "content": content
        })
        self.updated_at = datetime.now()
    
    def load_document(self, doc_id: str, content: str) -> None:
        """Загрузка документа в память"""
        # Проверка на превышение лимита
        if len(self.loaded_documents) >= MAX_MEMORY_DOCUMENTS:
            # Удаление самого старого документа
            self.loaded_documents.pop(0)
        
        self.loaded_documents.append({
            "id": doc_id,
            "content": content,
            "loaded_at": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def unload_document(self, doc_id: str) -> None:
        """Выгрузка документа из памяти"""
        self.loaded_documents = [doc for doc in self.loaded_documents if doc["id"] != doc_id]
        self.updated_at = datetime.now()
    
    def set_memory(self, key: str, value: Any) -> None:
        """Установка значения в память"""
        self.memory[key] = value
        self.updated_at = datetime.now()
    
    def get_memory(self, key: str, default: Any = None) -> Any:
        """Получение значения из памяти"""
        return self.memory.get(key, default)


class AutoCodeAnalyzer:
    """Класс для автоматического анализа кода"""
    
    def __init__(self, merged_file_path: str, db_path: str = DB_PATH):
        """
        Инициализация автоматического анализатора кода
        
        Args:
            merged_file_path: Путь к объединенному файлу с кодом
            db_path: Путь к файлу базы данных SQLite
        """
        self.merged_file_path = merged_file_path
        self.db_path = db_path
        
        # Создание необходимых директорий
        os.makedirs("logs", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("data/tasks", exist_ok=True)
        
        # Инициализация компонентов
        self.analyzer = MultiLanguageAnalyzer()
        self.chunker = CodeChunker()
        self.db = CodeKnowledgeDB(db_path)
        self.large_analyzer = LargeCSharpAnalyzer(merged_file_path, db_path)
        self.vector_search = QdrantCodeSearch(merged_file_path)
        
        # Очередь задач
        self.task_queue = PriorityQueue()
        self.tasks = {}  # task_id -> task
        
        # Запуск фонового обработчика задач
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._task_worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        logger.info(f"Автоматический анализатор кода инициализирован для файла: {merged_file_path}")
    
    def submit_task(self, query: str, priority: int = 1) -> str:
        """
        Отправка задачи на анализ
        
        Args:
            query: Запрос для анализа
            priority: Приоритет задачи (меньше = выше)
            
        Returns:
            str: Идентификатор задачи
        """
        # Генерация идентификатора задачи
        task_id = f"task_{int(time.time())}_{hash(query) % 10000}"
        
        # Создание задачи
        task = AutoAnalysisTask(task_id, query, priority)
        
        # Сохранение задачи
        self.tasks[task_id] = task
        self._save_task(task)
        
        # Добавление в очередь
        self.task_queue.put((priority, task_id))
        
        logger.info(f"Задача {task_id} отправлена на анализ с приоритетом {priority}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о задаче
        
        Args:
            task_id: Идентификатор задачи
            
        Returns:
            Optional[Dict[str, Any]]: Информация о задаче
        """
        task = self.tasks.get(task_id)
        if task:
            return task.to_dict()
        
        # Попытка загрузить из файла
        task = self._load_task(task_id)
        if task:
            return task.to_dict()
        
        return None
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        Получение информации о всех задачах
        
        Returns:
            List[Dict[str, Any]]: Информация о задачах
        """
        tasks = []
        
        # Задачи в памяти
        for task_id, task in self.tasks.items():
            tasks.append(task.to_dict())
        
        # Задачи в файлах
        task_dir = Path("data/tasks")
        if task_dir.exists():
            for task_file in task_dir.glob("*.json"):
                task_id = task_file.stem
                if task_id not in self.tasks:
                    task = self._load_task(task_id)
                    if task:
                        tasks.append(task.to_dict())
        
        return tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Отмена задачи
        
        Args:
            task_id: Идентификатор задачи
            
        Returns:
            bool: True, если задача отменена, иначе False
        """
        task = self.tasks.get(task_id)
        if task:
            task.status = "canceled"
            self._save_task(task)
            return True
        
        # Попытка загрузить из файла
        task = self._load_task(task_id)
        if task:
            task.status = "canceled"
            self._save_task(task)
            return True
        
        return False
    
    def _task_worker(self) -> None:
        """Фоновый обработчик задач"""
        while not self.stop_event.is_set():
            try:
                # Получение задачи из очереди с таймаутом
                try:
                    priority, task_id = self.task_queue.get(timeout=1)
                except:
                    continue
                
                # Получение задачи
                task = self.tasks.get(task_id)
                if not task:
                    task = self._load_task(task_id)
                
                if not task or task.status in ["completed", "failed", "canceled"]:
                    self.task_queue.task_done()
                    continue
                
                # Обработка задачи
                try:
                    task.status = "processing"
                    self._save_task(task)
                    
                    # Выполнение анализа
                    self._process_task(task)
                    
                    # Завершение задачи
                    task.status = "completed"
                    self._save_task(task)
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке задачи {task_id}: {str(e)}")
                    task.status = "failed"
                    task.result = {"error": str(e)}
                    self._save_task(task)
                
                finally:
                    self.task_queue.task_done()
            
            except Exception as e:
                logger.error(f"Ошибка в обработчике задач: {str(e)}")
    
    def _process_task(self, task: AutoAnalysisTask) -> None:
        """
        Обработка задачи анализа
        
        Args:
            task: Задача анализа
        """
        logger.info(f"Начало обработки задачи {task.task_id}")
        task.add_step("start", f"Начало анализа запроса: {task.query}")
        
        # Подготовка истории сообщений для LLM
        messages = [
            {"role": "system", "content": "Вы - автоматический ассистент для анализа кода C#. "
             "Ваша задача - исследовать код и найти ответы на вопросы. "
             "Вы можете самостоятельно искать нужные файлы, загружать их, анализировать и делать выводы. "
             "Будьте точны в своих ответах и ссылайтесь на конкретные части кода."},
            {"role": "user", "content": task.query}
        ]
        
        # Итеративный процесс анализа
        while task.iterations < MAX_ITERATIONS and task.status == "processing":
            task.iterations += 1
            
            # Проверка на отмену
            if task.status == "canceled":
                task.add_step("cancel", "Задача отменена пользователем")
                return
            
            try:
                # Запрос к LLM для определения следующего шага
                planning_prompt = (
                    "На основе предыдущих шагов анализа и запроса пользователя, определите, что нужно сделать дальше:\n"
                    "1. Какие файлы или классы нужно исследовать?\n"
                    "2. Какую информацию нужно получить?\n"
                    "3. Требуется ли выполнить дополнительные действия?"
                )
                
                messages.append({"role": "system", "content": planning_prompt})
                
                response = ollama.chat(
                    model=OLLAMA_MODEL,
                    messages=messages
                )
                
                plan = response.get("message", {}).get("content", "")
                task.add_step("plan", plan)
                
                # Определение действия на основе плана
                if "поиск" in plan.lower() or "найти" in plan.lower() or "search" in plan.lower():
                    # Извлечение запроса для поиска
                    search_queries = re.findall(r'поиск[а-я]*:?\s*["\']([^"\']+)["\']', plan, re.IGNORECASE)
                    search_queries.extend(re.findall(r'найти[а-я]*:?\s*["\']([^"\']+)["\']', plan, re.IGNORECASE))
                    search_queries.extend(re.findall(r'search[a-z]*:?\s*["\']([^"\']+)["\']', plan, re.IGNORECASE))
                    
                    search_query = search_queries[0] if search_queries else task.query
                    
                    # Выполнение поиска
                    self._perform_search(task, search_query)
                    
                elif "анализ" in plan.lower() or "analyze" in plan.lower():
                    # Извлечение имен файлов для анализа
                    file_patterns = re.findall(r'файл[а-я]*:?\s*["\']([^"\']+\.cs)["\']', plan, re.IGNORECASE)
                    file_patterns.extend(re.findall(r'class[a-z]*:?\s*["\']([^"\']+)["\']', plan, re.IGNORECASE))
                    
                    file_pattern = file_patterns[0] if file_patterns else None
                    
                    if file_pattern:
                        # Выполнение анализа файла
                        self._perform_analysis(task, file_pattern)
                    else:
                        # Общий анализ запроса
                        self._perform_general_analysis(task)
                
                else:
                    # Если нет явных указаний, делаем общий анализ
                    self._perform_general_analysis(task)
                
                # Проверка на достаточность информации
                if self._check_enough_information(task):
                    break
            
            except Exception as e:
                logger.error(f"Ошибка при итерации {task.iterations} задачи {task.task_id}: {str(e)}")
                task.add_step("error", f"Ошибка: {str(e)}")
        
        # Формирование итогового ответа
        self._generate_final_answer(task)
        
        # Очистка памяти
        for doc in task.loaded_documents:
            task.add_step("unload", f"Выгрузка документа: {doc['id']}")
        task.loaded_documents = []
        
        logger.info(f"Завершение обработки задачи {task.task_id}")
    
    def _perform_search(self, task: AutoAnalysisTask, query: str) -> None:
        """
        Выполнение поиска
        
        Args:
            task: Задача анализа
            query: Запрос для поиска
        """
        task.add_step("search", f"Поиск: {query}")
        
        try:
            # Поиск в векторной БД
            results = self.vector_search.search_code(query, top_k=3)
            
            if not results:
                task.add_step("search_result", "По запросу ничего не найдено")
                return
            
            # Добавление результатов в память
            search_results = []
            for i, result in enumerate(results):
                source = result.get("source", "")
                text = result.get("text", "")
                
                # Добавление в загруженные документы
                doc_id = f"search_{i}_{int(time.time())}"
                task.load_document(doc_id, text)
                
                search_results.append({
                    "doc_id": doc_id,
                    "source": source,
                    "snippet": text[:100] + "..." if len(text) > 100 else text
                })
            
            task.set_memory("search_results", search_results)
            task.add_step("search_result", f"Найдено {len(results)} результатов")
            
            # Добавление результатов поиска в контекст LLM
            search_context = "Результаты поиска:\n"
            for i, result in enumerate(search_results):
                search_context += f"{i+1}. Файл: {result['source']}\n"
                search_context += f"   Фрагмент: {result['snippet']}\n"
            
            # Добавление в историю сообщений
            messages = task.get_memory("messages", [])
            messages.append({"role": "system", "content": search_context})
            task.set_memory("messages", messages)
            
        except Exception as e:
            logger.error(f"Ошибка при поиске: {str(e)}")
            task.add_step("search_error", f"Ошибка при поиске: {str(e)}")
    
    def _perform_analysis(self, task: AutoAnalysisTask, file_pattern: str) -> None:
        """
        Выполнение анализа файла
        
        Args:
            task: Задача анализа
            file_pattern: Паттерн для поиска файла
        """
        task.add_step("analysis", f"Анализ файла: {file_pattern}")
        
        try:
            # Получение информации о файле
            if file_pattern.endswith(".cs"):
                # Это путь к файлу
                file_info = self.large_analyzer.get_file_info(file_pattern)
            else:
                # Это имя класса
                class_info = self.large_analyzer.get_class_info(file_pattern)
                
                if class_info and "error" not in class_info:
                    file_info = self.large_analyzer.get_file_info(class_info.get("file_path", ""))
                else:
                    file_info = None
            
            if not file_info or "error" in file_info:
                task.add_step("analysis_result", f"Файл не найден или ошибка анализа: {file_info.get('error', 'Неизвестная ошибка')}")
                return
            
            # Добавление информации о файле в память
            task.set_memory("file_info", file_info)
            
            # Добавление в контекст LLM
            file_context = f"Анализ файла: {file_info.get('file_path', '')}\n"
            file_context += f"Язык: {file_info.get('language', 'Неизвестно')}\n"
            file_context += f"Строк кода: {file_info.get('loc', 0)}\n"
            file_context += f"Классы: {', '.join(file_info.get('classes', []))}\n"
            file_context += f"Методы: {', '.join(file_info.get('methods', []))}\n"
            
            # Добавление в историю сообщений
            messages = task.get_memory("messages", [])
            messages.append({"role": "system", "content": file_context})
            task.set_memory("messages", messages)
            
            task.add_step("analysis_result", f"Анализ файла {file_info.get('file_path', '')} выполнен")
            
        except Exception as e:
            logger.error(f"Ошибка при анализе файла: {str(e)}")
            task.add_step("analysis_error", f"Ошибка при анализе файла: {str(e)}")
    
    def _perform_general_analysis(self, task: AutoAnalysisTask) -> None:
        """
        Выполнение общего анализа
        
        Args:
            task: Задача анализа
        """
        task.add_step("general_analysis", "Общий анализ запроса")
        
        try:
            # Выделение ключевых слов из запроса
            keywords = re.findall(r'\b([A-Z][a-zA-Z0-9]+)\b', task.query)
            
            if keywords:
                # Поиск информации о классах
                for keyword in keywords:
                    class_info = self.large_analyzer.get_class_info(keyword)
                    
                    if class_info and "error" not in class_info:
                        task.set_memory(f"class_info_{keyword}", class_info)
                        
                        # Добавление в контекст LLM
                        class_context = f"Информация о классе: {keyword}\n"
                        class_context += f"Файл: {class_info.get('file_path', 'Неизвестно')}\n"
                        class_context += f"Пространство имен: {class_info.get('namespace', 'Неизвестно')}\n"
                        class_context += f"Методы: {', '.join(class_info.get('methods', []))}\n"
                        
                        # Добавление в историю сообщений
                        messages = task.get_memory("messages", [])
                        messages.append({"role": "system", "content": class_context})
                        task.set_memory("messages", messages)
                        
                        task.add_step("class_info", f"Найдена информация о классе {keyword}")
            
            # Выполнение поиска по запросу
            self._perform_search(task, task.query)
            
        except Exception as e:
            logger.error(f"Ошибка при общем анализе: {str(e)}")
            task.add_step("general_analysis_error", f"Ошибка при общем анализе: {str(e)}")
    
    def _check_enough_information(self, task: AutoAnalysisTask) -> bool:
        """
        Проверка на достаточность информации для ответа
        
        Args:
            task: Задача анализа
            
        Returns:
            bool: True, если информации достаточно, иначе False
        """
        # Подготовка сообщений для LLM
        messages = [
            {"role": "system", "content": "Вы - автоматический ассистент для анализа кода C#. "
             "Оцените, достаточно ли у вас информации для ответа на вопрос пользователя."},
            {"role": "user", "content": task.query}
        ]
        
        # Добавление информации о шагах анализа
        steps_info = "Выполненные шаги анализа:\n"
        for step in task.analysis_steps:
            steps_info += f"- {step['action']}: {step['content'][:100]}...\n"
        
        messages.append({"role": "system", "content": steps_info})
        
        # Запрос к LLM
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages + [{"role": "user", "content": "Достаточно ли информации для ответа? Ответьте только Да или Нет."}]
        )
        
        answer = response.get("message", {}).get("content", "").lower()
        is_enough = "да" in answer and "нет" not in answer
        
        task.add_step("check_info", f"Проверка достаточности информации: {'Да' if is_enough else 'Нет'}")
        return is_enough
    
    def _generate_final_answer(self, task: AutoAnalysisTask) -> None:
        """
        Генерация итогового ответа
        
        Args:
            task: Задача анализа
        """
        task.add_step("final_answer", "Генерация итогового ответа")
        
        try:
            # Подготовка сообщений для LLM
            messages = [
                {"role": "system", "content": "Вы - автоматический ассистент для анализа кода C#. "
                 "На основе собранной информации дайте детальный ответ на вопрос пользователя. "
                 "Ссылайтесь на конкретные части кода и файлы, когда это возможно."},
                {"role": "user", "content": task.query}
            ]
            
            # Добавление информации о шагах анализа
            steps_info = "Собранная информация:\n"
            
            # Добавление информации о загруженных документах
            for doc in task.loaded_documents:
                doc_id = doc.get("id", "")
                source = doc.get("source", "Неизвестно") if "source" in doc else "Неизвестно"
                content_preview = doc.get("content", "")[:200] + "..." if len(doc.get("content", "")) > 200 else doc.get("content", "")
                
                steps_info += f"Документ {doc_id} из {source}:\n```\n{content_preview}\n```\n\n"
            
            messages.append({"role": "system", "content": steps_info})
            
            # Запрос к LLM
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages
            )
            
            answer = response.get("message", {}).get("content", "Не удалось сгенерировать ответ.")
            
            # Сохранение ответа
            task.result = {
                "answer": answer,
                "generated_at": datetime.now().isoformat(),
                "steps_count": len(task.analysis_steps),
                "documents_count": len(task.loaded_documents)
            }
            
            task.add_step("answer", f"Ответ сгенерирован: {answer[:100]}...")
            
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {str(e)}")
            task.add_step("answer_error", f"Ошибка при генерации ответа: {str(e)}")
            task.result = {"error": str(e)}
    
    def _save_task(self, task: AutoAnalysisTask) -> None:
        """
        Сохранение задачи в файл
        
        Args:
            task: Задача анализа
        """
        task_path = Path(f"data/tasks/{task.task_id}.json")
        task_data = task.to_dict()
        
        try:
            with open(task_path, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении задачи {task.task_id}: {str(e)}")
    
    def _load_task(self, task_id: str) -> Optional[AutoAnalysisTask]:
        """
        Загрузка задачи из файла
        
        Args:
            task_id: Идентификатор задачи
            
        Returns:
            Optional[AutoAnalysisTask]: Задача анализа
        """
        task_path = Path(f"data/tasks/{task_id}.json")
        
        if not task_path.exists():
            return None
        
        try:
            with open(task_path, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            task = AutoAnalysisTask.from_dict(task_data)
            return task
        
        except Exception as e:
            logger.error(f"Ошибка при загрузке задачи {task_id}: {str(e)}")
            return None
    
    def stop(self) -> None:
        """Остановка анализатора"""
        self.stop_event.set()
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)


def main():
    """Основная функция для запуска из командной строки"""
    import argparse
    from dotenv import load_dotenv
    
    # Загрузка переменных окружения
    load_dotenv()
    
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description="Автоматический анализатор кода C#")
    parser.add_argument("--file", type=str, help="Путь к объединенному файлу с кодом")
    parser.add_argument("--query", type=str, help="Запрос для анализа")
    
    args = parser.parse_args()
    
    # Путь к объединенному файлу
    merged_file = args.file or os.environ.get('MERGED_FILE_PATH', 'C:/Users/korda/YandexDisk/steelf/SteelF/merged_code.txt')
    
    if not os.path.exists(merged_file):
        print(f"Ошибка: Файл {merged_file} не найден")
        return
    
    # Создание анализатора
    analyzer = AutoCodeAnalyzer(merged_file)
    
    try:
        if args.query:
            # Выполнение анализа запроса
            task_id = analyzer.submit_task(args.query)
            print(f"Задача {task_id} отправлена на анализ")
            
            # Ожидание завершения задачи
            while True:
                task_info = analyzer.get_task(task_id)
                if task_info["status"] in ["completed", "failed", "canceled"]:
                    break
                time.sleep(1)
            
            # Вывод результата
            if task_info["status"] == "completed":
                print("\nРезультат анализа:")
                print(task_info["result"]["answer"])
            else:
                print(f"\nЗадача завершилась со статусом: {task_info['status']}")
                if "error" in task_info.get("result", {}):
                    print(f"Ошибка: {task_info['result']['error']}")
        else:
            # Интерактивный режим
            print("Автоматический анализатор кода C# запущен")
            print("Введите запрос для анализа или 'q' для выхода")
            
            while True:
                query = input("\nЗапрос> ")
                
                if query.lower() == 'q':
                    break
                
                if not query:
                    continue
                
                # Выполнение анализа запроса
                task_id = analyzer.submit_task(query)
                print(f"Задача {task_id} отправлена на анализ")
                
                # Ожидание завершения задачи с выводом прогресса
                print("Ожидание результатов...")
                while True:
                    task_info = analyzer.get_task(task_id)
                    status = task_info["status"]
                    iterations = task_info["iterations"]
                    
                    if status == "processing":
                        print(f"\rВыполнено итераций: {iterations}/{MAX_ITERATIONS}", end="")
                    
                    if status in ["completed", "failed", "canceled"]:
                        print("\nЗадача завершена!")
                        break
                    
                    time.sleep(1)
                
                # Вывод результата
                if task_info["status"] == "completed":
                    print("\nРезультат анализа:")
                    print(task_info["result"]["answer"])
                else:
                    print(f"\nЗадача завершилась со статусом: {task_info['status']}")
                    if "error" in task_info.get("result", {}):
                        print(f"Ошибка: {task_info['result']['error']}")
    
    except KeyboardInterrupt:
        print("\nРабота анализатора прервана пользователем")
    
    finally:
        # Остановка анализатора
        analyzer.stop()


if __name__ == "__main__":
    main() 