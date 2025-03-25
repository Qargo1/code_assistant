#!/usr/bin/env python3
"""
run_system.py - Запуск системы анализа кода C#

Скрипт для запуска всех компонентов системы анализа кода C# в одном процессе.
"""

import os
import sys
import argparse
import logging
import asyncio
import threading
import time
from pathlib import Path
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

def print_banner():
    """Вывод баннера системы"""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║   🚀 Code Assistant - Система анализа кода C#         ║
    ║                                                       ║
    ║   🔍 Векторный поиск | 📊 Анализ | 🤖 Auto LLM         ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    print(banner)

def check_environment():
    """Проверка окружения и зависимостей"""
    try:
        # Проверка наличия файла с кодом
        merged_file = os.environ.get('MERGED_FILE_PATH', 'C:/Users/korda/YandexDisk/steelf/SteelF/merged_code.txt')
        if not os.path.exists(merged_file):
            logger.warning(f"Файл с кодом не найден: {merged_file}")
            print(f"⚠️ Предупреждение: Файл с кодом не найден: {merged_file}")
            print("  Укажите путь к файлу в переменной MERGED_FILE_PATH или создайте его.")
        
        # Проверка наличия токена Telegram
        telegram_token = os.environ.get('TELEGRAM_TOKEN')
        if not telegram_token:
            logger.warning("Токен Telegram не найден в переменных окружения")
            print("⚠️ Предупреждение: Токен Telegram не найден в переменных окружения")
            print("  Укажите токен в переменной TELEGRAM_TOKEN для включения бота.")
        
        # Проверка наличия моделей Ollama
        try:
            import ollama
            models = ollama.list()
            has_qwen = any("qwen" in model["name"].lower() for model in models.get("models", []))
            
            if not has_qwen:
                logger.warning("Модель qwen2.5-coder:3b не найдена в Ollama")
                print("⚠️ Предупреждение: Модель qwen2.5-coder:3b не найдена в Ollama")
                print("  Выполните 'ollama pull qwen2.5-coder:3b' или используйте другую модель.")
        
        except Exception as e:
            logger.warning(f"Не удалось проверить модели Ollama: {str(e)}")
            print(f"⚠️ Предупреждение: Не удалось проверить модели Ollama: {str(e)}")
        
        # Проверка наличия директорий
        for dir_name in ["logs", "data", "qdrant_storage"]:
            os.makedirs(dir_name, exist_ok=True)
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке окружения: {str(e)}")
        print(f"❌ Ошибка при проверке окружения: {str(e)}")
        return False

def start_telegram_bot(token):
    """Запуск Telegram бота"""
    try:
        from interfaces.telegram_code_assistant import CodeAssistantBot
        
        bot = CodeAssistantBot(token)
        return asyncio.run(bot.start_bot())
    
    except Exception as e:
        logger.error(f"Ошибка при запуске Telegram бота: {str(e)}")
        print(f"❌ Ошибка при запуске Telegram бота: {str(e)}")

def start_code_analyzer(merged_file_path):
    """Запуск анализатора кода"""
    try:
        from automation.auto_code_analyzer import AutoCodeAnalyzer
        
        analyzer = AutoCodeAnalyzer(merged_file_path)
        
        # Запускаем примерную задачу для инициализации
        analyzer.submit_task("Подготовка системы и инициализация компонентов", priority=10)
        
        return analyzer
    
    except Exception as e:
        logger.error(f"Ошибка при запуске анализатора кода: {str(e)}")
        print(f"❌ Ошибка при запуске анализатора кода: {str(e)}")
        return None

def start_all_components():
    """Запуск всех компонентов системы"""
    try:
        # Получение переменных окружения
        merged_file = os.environ.get('MERGED_FILE_PATH', 'C:/Users/korda/YandexDisk/steelf/SteelF/merged_code.txt')
        telegram_token = os.environ.get('TELEGRAM_TOKEN')
        
        components = {}
        
        # Запуск анализатора кода
        logger.info("Запуск анализатора кода...")
        print("🔄 Запуск анализатора кода...")
        
        analyzer = start_code_analyzer(merged_file)
        if analyzer:
            components["analyzer"] = analyzer
            logger.info("Анализатор кода запущен успешно")
            print("✅ Анализатор кода запущен успешно")
        
        # Запуск Telegram бота в отдельном потоке, если есть токен
        if telegram_token:
            logger.info("Запуск Telegram бота...")
            print("🔄 Запуск Telegram бота...")
            
            # Запускаем бота в отдельном потоке
            bot_thread = threading.Thread(
                target=start_telegram_bot,
                args=(telegram_token,),
                daemon=True
            )
            bot_thread.start()
            
            components["bot_thread"] = bot_thread
            logger.info("Telegram бот запущен успешно")
            print("✅ Telegram бот запущен успешно")
        
        return components
    
    except Exception as e:
        logger.error(f"Ошибка при запуске компонентов: {str(e)}")
        print(f"❌ Ошибка при запуске компонентов: {str(e)}")
        return {}

def stop_components(components):
    """Остановка всех компонентов системы"""
    try:
        # Остановка анализатора кода
        if "analyzer" in components:
            logger.info("Остановка анализатора кода...")
            print("🔄 Остановка анализатора кода...")
            
            components["analyzer"].stop()
            
            logger.info("Анализатор кода остановлен")
            print("✅ Анализатор кода остановлен")
        
        # Остановка Telegram бота
        if "bot_thread" in components:
            logger.info("Остановка Telegram бота...")
            print("🔄 Остановка Telegram бота...")
            
            # Для бота нет явного метода остановки, ждем завершения потока
            if components["bot_thread"].is_alive():
                components["bot_thread"].join(timeout=5)
            
            logger.info("Telegram бот остановлен")
            print("✅ Telegram бот остановлен")
    
    except Exception as e:
        logger.error(f"Ошибка при остановке компонентов: {str(e)}")
        print(f"❌ Ошибка при остановке компонентов: {str(e)}")

def run_interactive_mode(components):
    """Запуск интерактивного режима"""
    try:
        print("\n📋 Интерактивный режим запущен")
        print("Доступные команды:")
        print("  analyze <запрос> - Анализ кода")
        print("  status - Статус системы")
        print("  exit - Выход из системы")
        
        analyzer = components.get("analyzer")
        
        while True:
            try:
                command = input("\nCommand> ").strip()
                
                if not command:
                    continue
                
                if command.lower() == "exit":
                    break
                
                elif command.lower() == "status":
                    # Вывод статуса компонентов
                    print("\n📊 Статус системы:")
                    
                    if analyzer:
                        task_count = len(analyzer.get_all_tasks())
                        print(f"  Анализатор кода: Активен (задач: {task_count})")
                    else:
                        print("  Анализатор кода: Неактивен")
                    
                    if "bot_thread" in components:
                        bot_status = "Активен" if components["bot_thread"].is_alive() else "Неактивен"
                        print(f"  Telegram бот: {bot_status}")
                    else:
                        print("  Telegram бот: Не запущен")
                
                elif command.lower().startswith("analyze "):
                    # Запуск анализа кода
                    query = command[8:].strip()
                    
                    if not query:
                        print("❌ Необходимо указать запрос для анализа")
                        continue
                    
                    if not analyzer:
                        print("❌ Анализатор кода не запущен")
                        continue
                    
                    # Запуск задачи анализа
                    task_id = analyzer.submit_task(query)
                    print(f"✅ Задача {task_id} отправлена на анализ")
                    
                    # Ожидание результатов с индикацией
                    print("🔄 Ожидание результатов...")
                    
                    while True:
                        task_info = analyzer.get_task(task_id)
                        status = task_info["status"]
                        iterations = task_info["iterations"]
                        
                        if status == "processing":
                            print(f"\rВыполнено итераций: {iterations}/5", end="")
                        
                        if status in ["completed", "failed", "canceled"]:
                            print("\n✅ Задача завершена!")
                            break
                        
                        time.sleep(1)
                    
                    # Вывод результата
                    if task_info["status"] == "completed":
                        print("\n📝 Результат анализа:")
                        print(task_info["result"]["answer"])
                    else:
                        print(f"\n❌ Задача завершилась со статусом: {task_info['status']}")
                        if "error" in task_info.get("result", {}):
                            print(f"Ошибка: {task_info['result']['error']}")
                
                else:
                    print(f"❌ Неизвестная команда: {command}")
            
            except KeyboardInterrupt:
                print("\n⚠️ Прервано пользователем")
                break
            
            except Exception as e:
                print(f"❌ Ошибка при выполнении команды: {str(e)}")
        
        print("\n👋 Выход из интерактивного режима")
    
    except Exception as e:
        logger.error(f"Ошибка в интерактивном режиме: {str(e)}")
        print(f"❌ Ошибка в интерактивном режиме: {str(e)}")

def main():
    """Основная функция"""
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description="Запуск системы анализа кода C#")
    parser.add_argument("--interactive", action="store_true", help="Запуск в интерактивном режиме")
    parser.add_argument("--analyze", type=str, help="Запрос для анализа")
    parser.add_argument("--telegram-only", action="store_true", help="Запуск только Telegram бота")
    parser.add_argument("--analyzer-only", action="store_true", help="Запуск только анализатора кода")
    
    args = parser.parse_args()
    
    # Вывод баннера
    print_banner()
    
    # Проверка окружения
    if not check_environment():
        return
    
    try:
        # Запуск компонентов
        components = start_all_components()
        
        if not components:
            logger.error("Не удалось запустить ни один компонент системы")
            print("❌ Не удалось запустить ни один компонент системы")
            return
        
        # Обработка режимов запуска
        if args.analyze:
            # Запуск анализа конкретного запроса
            analyzer = components.get("analyzer")
            
            if not analyzer:
                logger.error("Анализатор кода не запущен")
                print("❌ Анализатор кода не запущен")
                return
            
            print(f"🔍 Анализ запроса: {args.analyze}")
            
            # Запуск задачи анализа
            task_id = analyzer.submit_task(args.analyze)
            print(f"✅ Задача {task_id} отправлена на анализ")
            
            # Ожидание результатов с индикацией
            print("🔄 Ожидание результатов...")
            
            while True:
                task_info = analyzer.get_task(task_id)
                status = task_info["status"]
                iterations = task_info["iterations"]
                
                if status == "processing":
                    print(f"\rВыполнено итераций: {iterations}/5", end="")
                
                if status in ["completed", "failed", "canceled"]:
                    print("\n✅ Задача завершена!")
                    break
                
                time.sleep(1)
            
            # Вывод результата
            if task_info["status"] == "completed":
                print("\n📝 Результат анализа:")
                print(task_info["result"]["answer"])
            else:
                print(f"\n❌ Задача завершилась со статусом: {task_info['status']}")
                if "error" in task_info.get("result", {}):
                    print(f"Ошибка: {task_info['result']['error']}")
        
        elif args.interactive:
            # Запуск в интерактивном режиме
            run_interactive_mode(components)
        
        else:
            # Запуск в фоновом режиме
            print("\n✅ Система запущена и работает в фоновом режиме")
            print("Для остановки нажмите Ctrl+C")
            
            try:
                # Ожидание прерывания пользователем
                while True:
                    time.sleep(1)
            
            except KeyboardInterrupt:
                print("\n\n⚠️ Получен сигнал остановки")
        
        # Остановка компонентов
        print("\n🔄 Остановка системы...")
        stop_components(components)
        print("✅ Система остановлена")
    
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        print(f"\n❌ Критическая ошибка: {str(e)}")
    
    finally:
        print("\n👋 Завершение работы системы")


if __name__ == "__main__":
    main() 