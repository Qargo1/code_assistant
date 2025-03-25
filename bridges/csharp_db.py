"""
Мост для работы с базой данных через C# сервис.
Обеспечивает доступ к данным, полученным при сканировании исходного кода C#.
"""

import logging
import os
import json
import sqlite3
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
import threading
from functools import lru_cache

logger = logging.getLogger(__name__)

class CSharpDBBridge:
    """
    Класс для взаимодействия с C# сервисом, обеспечивающим
    доступ к базе данных с информацией о коде.
    """
    
    def __init__(self, exe_path=None, db_path=None):
        """
        Инициализация моста.
        
        Args:
            exe_path: Путь к исполняемому файлу C# сервиса.
                      Если None, используется значение по умолчанию.
            db_path: Путь к файлу базы данных SQLite.
                     Если None, используется значение по умолчанию.
        """
        self.exe_path = exe_path or os.path.join(
            Path(__file__).parent.parent,
            "resources", "DatabaseService.exe"
        )
        self.db_path = db_path or os.path.join(
            Path(__file__).parent.parent,
            "data", "code_knowledge.db"
        )
        
        # Инициализация локальной базы данных, если не существует
        self._ensure_db_exists()
        
        self.lock = threading.Lock()
        logger.info(f"Initialized CSharpDBBridge with DB path: {self.db_path}")
    
    def _ensure_db_exists(self):
        """Проверка и создание базы данных, если не существует"""
        if not os.path.exists(self.db_path):
            logger.info(f"Creating new database at {self.db_path}")
            
            # Создание директории, если не существует
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Создание пустой базы данных с необходимыми таблицами
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Создание таблиц
            c.execute('''
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    namespace TEXT,
                    file_path TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS methods (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    class_id INTEGER,
                    return_type TEXT,
                    parameters TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (class_id) REFERENCES classes (id)
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS usages (
                    id INTEGER PRIMARY KEY,
                    source_id INTEGER,
                    source_type TEXT,
                    target_id INTEGER,
                    target_type TEXT,
                    file_path TEXT,
                    line_number INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Индексы для ускорения поиска
            c.execute('CREATE INDEX IF NOT EXISTS idx_classes_name ON classes (name)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_methods_name ON methods (name)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_methods_class ON methods (class_id)')
            
            conn.commit()
            conn.close()
    
    def execute_query(self, query):
        """
        Выполнение SQL-запроса к базе данных.
        
        Args:
            query: SQL-запрос для выполнения
            
        Returns:
            Результат запроса в виде JSON-строки
        """
        logger.info(f"Executing query: {query}")
        
        # Проверка доступности C# сервиса
        if os.path.exists(self.exe_path):
            return self._execute_via_service(query)
        else:
            logger.warning("C# service not available, using direct SQLite mode")
            return self._execute_direct(query)
    
    def _execute_via_service(self, query):
        """Выполнение запроса через C# сервис"""
        try:
            # Создание временного файла для передачи запроса
            fd, query_file = tempfile.mkstemp(suffix='.sql')
            os.close(fd)
            
            with open(query_file, 'w') as f:
                f.write(query)
            
            # Выполнение C# сервиса
            result = subprocess.run(
                [self.exe_path, self.db_path, query_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Удаление временного файла
            os.unlink(query_file)
            
            # Обработка результата
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Query failed: {result.stderr}")
                return json.dumps({
                    "error": True,
                    "message": f"Error executing query: {result.stderr}"
                })
                
        except Exception as e:
            logger.exception(f"Error executing query via C# service: {str(e)}")
            return json.dumps({
                "error": True,
                "message": f"Internal error: {str(e)}"
            })
    
    def _execute_direct(self, query):
        """Прямое выполнение запроса через Python SQLite"""
        with self.lock:
            try:
                # Подключение к базе данных
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Проверка типа запроса
                query_type = query.strip().upper().split()[0]
                
                # Выполнение запроса
                cursor.execute(query)
                
                # Для SELECT возвращаем результаты
                if query_type == 'SELECT':
                    rows = cursor.fetchall()
                    result = []
                    for row in rows:
                        result.append(dict(row))
                    
                    conn.close()
                    return json.dumps({
                        "error": False,
                        "rows": result,
                        "count": len(result)
                    })
                
                # Для INSERT/UPDATE/DELETE возвращаем количество затронутых строк
                else:
                    affected = cursor.rowcount
                    conn.commit()
                    conn.close()
                    return json.dumps({
                        "error": False,
                        "affected_rows": affected,
                        "message": f"Query executed successfully. Affected rows: {affected}"
                    })
                    
            except Exception as e:
                logger.exception(f"Error executing direct query: {str(e)}")
                return json.dumps({
                    "error": True,
                    "message": f"SQLite error: {str(e)}"
                })
    
    @lru_cache(maxsize=100)
    def get_class_info(self, class_name):
        """
        Получение информации о классе по имени.
        
        Args:
            class_name: Имя класса
            
        Returns:
            Словарь с информацией о классе
        """
        query = f"SELECT * FROM classes WHERE name = '{class_name}' LIMIT 1"
        result = self.execute_query(query)
        
        try:
            data = json.loads(result)
            if data.get("error", True):
                return None
            
            if data.get("rows") and len(data["rows"]) > 0:
                return data["rows"][0]
            
            return None
        except Exception as e:
            logger.error(f"Error parsing class info: {str(e)}")
            return None
    
    def find_usages(self, entity_id, entity_type):
        """
        Поиск использований класса или метода.
        
        Args:
            entity_id: ID сущности (класса или метода)
            entity_type: Тип сущности ('class' или 'method')
            
        Returns:
            Список мест использования
        """
        query = f"""
            SELECT u.*, 
                  c.name as source_name, 
                  m.name as target_name
            FROM usages u
            LEFT JOIN classes c ON u.source_id = c.id AND u.source_type = 'class'
            LEFT JOIN methods m ON u.target_id = m.id AND u.target_type = 'method'
            WHERE (u.source_id = {entity_id} AND u.source_type = '{entity_type}')
               OR (u.target_id = {entity_id} AND u.target_type = '{entity_type}')
            ORDER BY u.file_path, u.line_number
        """
        
        result = self.execute_query(query)
        
        try:
            data = json.loads(result)
            if data.get("error", True):
                return []
            
            return data.get("rows", [])
        except Exception as e:
            logger.error(f"Error parsing usages: {str(e)}")
            return [] 