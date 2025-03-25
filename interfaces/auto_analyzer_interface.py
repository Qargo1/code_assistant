#!/usr/bin/env python3
"""
auto_analyzer_interface.py - Интерфейс для автоматического анализатора кода C#

Модуль предоставляет интерфейс для автоматического анализатора кода C#,
который может использоваться различными компонентами системы,
включая Telegram-бот и веб-интерфейс.
"""

import os
import sys
import json
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Импорт модулей проекта
from automation.auto_code_analyzer import AutoCodeAnalyzer, AutoAnalysisTask

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


class AutoAnalyzerInterface:
    """Интерфейс для автоматического анализатора кода"""
    
    def __init__(self, merged_file_path: str = None):
        """
        Инициализация интерфейса для анализатора кода
        
        Args:
            merged_file_path: Путь к объединенному файлу с кодом
        """
        # Получение пути к файлу из переменных окружения, если не указан
        if not merged_file_path:
            merged_file_path = os.environ.get('MERGED_FILE_PATH', 'C:/Users/korda/YandexDisk/steelf/SteelF/merged_code.txt')
        
        # Проверка существования файла
        if not os.path.exists(merged_file_path):
            logger.warning(f"Файл кода не найден: {merged_file_path}")
            print(f"⚠️ Файл кода не найден: {merged_file_path}")
        
        # Инициализация анализатора
        try:
            self.analyzer = AutoCodeAnalyzer(merged_file_path)
            logger.info("AutoCodeAnalyzer инициализирован успешно")
        except Exception as e:
            logger.error(f"Ошибка при инициализации AutoCodeAnalyzer: {str(e)}")
            self.analyzer = None
        
        # Кэш результатов для быстрого доступа
        self.results_cache = {}
        
        # Запуск фоновой задачи для обновления кэша
        self.running = True
        self.update_thread = threading.Thread(target=self._update_cache_worker, daemon=True)
        self.update_thread.start()
    
    def stop(self):
        """Остановка интерфейса"""
        if self.analyzer:
            self.analyzer.stop()
        
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
    
    def _update_cache_worker(self):
        """Фоновая задача для обновления кэша результатов"""
        while self.running:
            try:
                if self.analyzer:
                    # Получение всех задач
                    tasks = self.analyzer.get_all_tasks()
                    
                    # Обновление кэша
                    for task_id, task_info in tasks.items():
                        if task_info["status"] == "completed" and task_id not in self.results_cache:
                            self.results_cache[task_id] = task_info["result"]["answer"]
            
            except Exception as e:
                logger.error(f"Ошибка при обновлении кэша: {str(e)}")
            
            # Ожидание перед следующим обновлением
            time.sleep(5)
    
    def submit_analysis_task(self, query: str, priority: int = 5) -> Optional[str]:
        """
        Отправка задачи на анализ
        
        Args:
            query: Запрос для анализа
            priority: Приоритет задачи (от 1 до 10, где 10 - высший)
            
        Returns:
            ID задачи или None в случае ошибки
        """
        if not self.analyzer:
            logger.error("Анализатор не инициализирован")
            return None
        
        try:
            # Отправка задачи на анализ
            task_id = self.analyzer.submit_task(query, priority=priority)
            logger.info(f"Отправлена задача на анализ: {task_id}")
            return task_id
        
        except Exception as e:
            logger.error(f"Ошибка при отправке задачи на анализ: {str(e)}")
            return None
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение статуса задачи
        
        Args:
            task_id: ID задачи
            
        Returns:
            Информация о задаче или None в случае ошибки
        """
        if not self.analyzer:
            logger.error("Анализатор не инициализирован")
            return None
        
        try:
            # Получение информации о задаче
            task_info = self.analyzer.get_task(task_id)
            
            if not task_info:
                logger.warning(f"Задача не найдена: {task_id}")
                return None
            
            return task_info
        
        except Exception as e:
            logger.error(f"Ошибка при получении статуса задачи: {str(e)}")
            return None
    
    def get_result(self, task_id: str) -> Optional[str]:
        """
        Получение результата анализа
        
        Args:
            task_id: ID задачи
            
        Returns:
            Результат анализа или None в случае ошибки
        """
        # Проверка кэша
        if task_id in self.results_cache:
            return self.results_cache[task_id]
        
        if not self.analyzer:
            logger.error("Анализатор не инициализирован")
            return None
        
        try:
            # Получение информации о задаче
            task_info = self.analyzer.get_task(task_id)
            
            if not task_info:
                logger.warning(f"Задача не найдена: {task_id}")
                return None
            
            # Проверка статуса задачи
            if task_info["status"] != "completed":
                logger.warning(f"Задача не завершена: {task_id}, статус: {task_info['status']}")
                return None
            
            # Получение результата
            result = task_info["result"]["answer"]
            
            # Обновление кэша
            self.results_cache[task_id] = result
            
            return result
        
        except Exception as e:
            logger.error(f"Ошибка при получении результата анализа: {str(e)}")
            return None
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Отмена задачи
        
        Args:
            task_id: ID задачи
            
        Returns:
            True, если задача успешно отменена, иначе False
        """
        if not self.analyzer:
            logger.error("Анализатор не инициализирован")
            return False
        
        try:
            # Отмена задачи
            success = self.analyzer.cancel_task(task_id)
            
            if success:
                logger.info(f"Задача отменена: {task_id}")
            else:
                logger.warning(f"Не удалось отменить задачу: {task_id}")
            
            return success
        
        except Exception as e:
            logger.error(f"Ошибка при отмене задачи: {str(e)}")
            return False
    
    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение списка последних задач
        
        Args:
            limit: Максимальное количество задач
            
        Returns:
            Список задач
        """
        if not self.analyzer:
            logger.error("Анализатор не инициализирован")
            return []
        
        try:
            # Получение всех задач
            all_tasks = self.analyzer.get_all_tasks()
            
            # Сортировка задач по времени создания (от новых к старым)
            sorted_tasks = sorted(
                all_tasks.items(),
                key=lambda x: x[1]["created_at"],
                reverse=True
            )
            
            # Ограничение количества задач
            sorted_tasks = sorted_tasks[:limit]
            
            # Преобразование в список словарей
            result = []
            for task_id, task_info in sorted_tasks:
                task_data = {
                    "task_id": task_id,
                    "query": task_info["query"],
                    "status": task_info["status"],
                    "iterations": task_info["iterations"],
                    "created_at": task_info["created_at"],
                    "updated_at": task_info["updated_at"]
                }
                
                if task_info["status"] == "completed":
                    task_data["has_result"] = True
                
                result.append(task_data)
            
            return result
        
        except Exception as e:
            logger.error(f"Ошибка при получении списка задач: {str(e)}")
            return []
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Получение списка активных задач
        
        Returns:
            Список активных задач
        """
        if not self.analyzer:
            logger.error("Анализатор не инициализирован")
            return []
        
        try:
            # Получение всех задач
            all_tasks = self.analyzer.get_all_tasks()
            
            # Фильтрация по статусу
            active_tasks = []
            for task_id, task_info in all_tasks.items():
                if task_info["status"] in ["pending", "processing"]:
                    active_tasks.append({
                        "task_id": task_id,
                        "query": task_info["query"],
                        "status": task_info["status"],
                        "iterations": task_info["iterations"],
                        "priority": task_info["priority"],
                        "created_at": task_info["created_at"],
                        "updated_at": task_info["updated_at"]
                    })
            
            # Сортировка по приоритету и времени создания
            active_tasks.sort(
                key=lambda x: (-x["priority"], x["created_at"])
            )
            
            return active_tasks
        
        except Exception as e:
            logger.error(f"Ошибка при получении списка активных задач: {str(e)}")
            return []
    
    def search_similar_tasks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск похожих задач по запросу
        
        Args:
            query: Запрос для поиска
            limit: Максимальное количество задач
            
        Returns:
            Список похожих задач
        """
        if not self.analyzer:
            logger.error("Анализатор не инициализирован")
            return []
        
        try:
            # Получение всех задач
            all_tasks = self.analyzer.get_all_tasks()
            
            # Поиск похожих задач (простой поиск по словам из запроса)
            query_words = set(query.lower().split())
            similar_tasks = []
            
            for task_id, task_info in all_tasks.items():
                if task_info["status"] == "completed":
                    task_query = task_info["query"].lower()
                    task_words = set(task_query.split())
                    
                    # Подсчет пересечения слов
                    intersection = query_words.intersection(task_words)
                    similarity = len(intersection) / max(1, len(query_words))
                    
                    if similarity > 0.3:  # Минимальный порог схожести
                        similar_tasks.append({
                            "task_id": task_id,
                            "query": task_info["query"],
                            "similarity": similarity,
                            "created_at": task_info["created_at"]
                        })
            
            # Сортировка по схожести
            similar_tasks.sort(key=lambda x: -x["similarity"])
            
            # Ограничение количества результатов
            return similar_tasks[:limit]
        
        except Exception as e:
            logger.error(f"Ошибка при поиске похожих задач: {str(e)}")
            return []
    
    def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение подробной информации о задаче
        
        Args:
            task_id: ID задачи
            
        Returns:
            Подробная информация о задаче или None в случае ошибки
        """
        if not self.analyzer:
            logger.error("Анализатор не инициализирован")
            return None
        
        try:
            # Получение информации о задаче
            task_info = self.analyzer.get_task(task_id)
            
            if not task_info:
                logger.warning(f"Задача не найдена: {task_id}")
                return None
            
            # Форматирование результата
            result = {
                "task_id": task_id,
                "query": task_info["query"],
                "status": task_info["status"],
                "priority": task_info["priority"],
                "iterations": task_info["iterations"],
                "created_at": task_info["created_at"],
                "updated_at": task_info["updated_at"],
                "analysis_steps": task_info["analysis_steps"],
                "loaded_documents": task_info["loaded_documents"]
            }
            
            # Проверка наличия результата
            if task_info["status"] == "completed" and "result" in task_info:
                result["result"] = task_info["result"]["answer"]
            
            return result
        
        except Exception as e:
            logger.error(f"Ошибка при получении информации о задаче: {str(e)}")
            return None
    
    def is_ready(self) -> bool:
        """
        Проверка готовности анализатора
        
        Returns:
            True, если анализатор готов к работе, иначе False
        """
        return self.analyzer is not None
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Получение статистики системы
        
        Returns:
            Статистика системы
        """
        stats = {
            "status": "not_initialized",
            "ready": False,
            "tasks": {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "processing": 0,
                "canceled": 0
            },
            "performance": {
                "avg_processing_time": 0,
                "avg_iterations": 0
            }
        }
        
        if not self.analyzer:
            return stats
        
        try:
            # Статус анализатора
            stats["status"] = "ready"
            stats["ready"] = True
            
            # Получение всех задач
            all_tasks = self.analyzer.get_all_tasks()
            
            # Подсчет задач по статусам
            stats["tasks"]["total"] = len(all_tasks)
            
            processing_times = []
            iterations_count = []
            
            for task_id, task_info in all_tasks.items():
                status = task_info["status"]
                stats["tasks"][status] = stats["tasks"].get(status, 0) + 1
                
                # Сбор данных для расчета среднего времени обработки и итераций
                if status == "completed" and "created_at" in task_info and "updated_at" in task_info:
                    created = datetime.fromisoformat(task_info["created_at"])
                    updated = datetime.fromisoformat(task_info["updated_at"])
                    processing_time = (updated - created).total_seconds()
                    processing_times.append(processing_time)
                    
                    iterations_count.append(task_info["iterations"])
            
            # Расчет средних значений
            if processing_times:
                stats["performance"]["avg_processing_time"] = sum(processing_times) / len(processing_times)
            
            if iterations_count:
                stats["performance"]["avg_iterations"] = sum(iterations_count) / len(iterations_count)
            
            return stats
        
        except Exception as e:
            logger.error(f"Ошибка при получении статистики системы: {str(e)}")
            stats["status"] = "error"
            stats["error"] = str(e)
            return stats


# Пример использования
def main():
    """Основная функция для тестирования интерфейса"""
    from dotenv import load_dotenv
    
    # Загрузка переменных окружения
    load_dotenv()
    
    # Инициализация интерфейса
    interface = AutoAnalyzerInterface()
    
    if not interface.is_ready():
        print("❌ Ошибка: Анализатор не инициализирован")
        return
    
    # Пример отправки задачи на анализ
    task_id = interface.submit_analysis_task("Расскажи о структуре UserService в проекте")
    
    if task_id:
        print(f"✅ Задача отправлена на анализ: {task_id}")
        
        # Ожидание результата
        max_wait = 60  # Максимальное время ожидания в секундах
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status = interface.get_task_status(task_id)
            
            if status and status["status"] in ["completed", "failed", "canceled"]:
                print(f"✅ Задача завершена со статусом: {status['status']}")
                
                if status["status"] == "completed":
                    result = interface.get_result(task_id)
                    print(f"📄 Результат анализа:\n{result}")
                
                break
            
            print(f"⏳ Ожидание результата... Статус: {status['status']}, Итерации: {status['iterations']}")
            time.sleep(5)
        
        if time.time() - start_time >= max_wait:
            print("⚠️ Превышено время ожидания результата")
    
    # Получение статистики системы
    stats = interface.get_system_stats()
    print(f"📊 Статистика системы: {json.dumps(stats, indent=2)}")
    
    # Остановка интерфейса
    interface.stop()


if __name__ == "__main__":
    main() 