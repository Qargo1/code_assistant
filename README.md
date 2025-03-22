<a name="english-version"></a>

```markdown
# 🚀 Code Assistant: Intelligent Multi-Language Development Toolkit

**AI-powered code analysis system** with LLM integration, semantic search, and cross-language refactoring support.  
✨ Features: Python/C#/Java/JS | 🔍 Vector Search | 🤖 Telegram Bot | 📊 Monitoring | 🔄 CI/CD Pipelines

> **STATUS NOTICE**  
> This project is currently in **active development phase** and is not yet production-ready. Core functionalities are experimental, and APIs may change without prior notice.

---

## 🌍 Language Quick Jump
[Russian Version](#русская-версия) | [English Version](#english-version)

---

## 🛠 Quick Start

### 1. Prerequisites Installation
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[all]
```

### 2. Infrastructure Setup
```bash
# PostgreSQL Configuration
sudo -u postgres psql -c "CREATE DATABASE code_knowledge;"
sudo -u postgres psql -c "CREATE USER codebot WITH PASSWORD 'securepass';"

# Redis & Qdrant Services
docker-compose up -d  # Core services
docker-compose -f docker-compose.monitoring.yml up -d  # Monitoring stack
```

### 3. System Initialization
```python
from core.vector_db.qdrant_connector import VectorSearchEngine
engine = VectorSearchEngine()
engine.init_embedder(model_name="google/flan-t5-small")  # Quantized model
```

---

## 🔧 Core Capabilities

### 🧠 Semantic Code Analysis
```python
from core.analysis.filter import FileFilter
filter = FileFilter()
print(filter.check_relevance("src/auth.py", "authentication system"))  # → {"relevance": 0.94}
```

### ⚡️ Task Queue Management
```bash
rq worker high medium low --with-scheduler  # Run in separate terminal
```

### 🤖 Telegram Integration
```bash
echo "TELEGRAM_TOKEN=your_bot_token" > .env
python -m interfaces.telegram.bot_core
```

---

## 📦 System Components

| Service          | Purpose                          | Launch Command                    |
|------------------|----------------------------------|-----------------------------------|
| **Java Service** | Secure Terminal Operations       | `cd bridges/java/SecureTerminal && mvn package` |
| **C# Service**   | Database Integration            | `cd bridges/csharp/DatabaseService && dotnet run` |
| **Monitoring**   | Grafana + Prometheus Dashboard  | `http://localhost:3000/dashboards` |

---

## 🧪 Testing Suite
```bash
# Run all tests with verbose output
pytest tests/ -v

# Expected output:
# ✔ test_basic_setup (3 passed)
# ✔ test_vector_search (89% coverage)
```

---

## 🚨 Troubleshooting Guide

**Issue**: Redis Connection Failures  
**Solution**: 
```bash
redis-cli ping  # Verify connectivity
sudo systemctl restart redis
```

**Issue**: Missing spaCy Models  
**Solution**:
```bash
python -m spacy download en_core_web_sm
```

---

## 🏗 Integration Examples

### Code Refactoring
```python
from core.refactor.code_analyzer import CodeRefactorer
refactorer = CodeRefactorer()
result = refactorer.analyze_file("src/auth.py")  # → Optimization suggestions
```

### Version Control Integration
```python
from core.vcs.git_integration import GitManager
manager = GitManager(".")
print(manager.get_changed_files("HEAD~3..HEAD"))  # → Change list
```

---

## 📄 License  
MIT License | Full details in `LICENSE.md`

[![Live Demo Preview](https://img.shields.io/badge/Demo-Video-blue)](https://example.com/demo)

---

**Key Enhancements:**  
1. Added **development status warning** with professional phrasing  
2. Implemented **language switch anchors** for navigation  
3. Unified terminology across both language versions  
4. Maintained visual consistency with emojis and tables  
5. Improved command-line examples for international audiences  
6. Added explicit API stability disclaimer  
7. Standardized documentation structure between languages

<a name="русская-версия"></a>

```markdown
# 🚀 Code Assistant: Умный помощник для разработки с поддержкой мультиязычного анализа
# Currently IN DEVELOPMENT

**Интеллектуальная система для автоматизации разработки** с интеграцией LLM, семантическим поиском кода и кросс-языковым анализом.  
✨ Поддерживает: Python, C#, Java, JS | 🔍 Векторный поиск | 🤖 Telegram-бот | 📊 Мониторинг | 🔄 CI/CD пайплайны
```

---

## 🛠 Быстрый старт

### 1. Установка зависимостей
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[all]
```

### 2. Настройка окружения
```bash
# PostgreSQL
sudo -u postgres psql -c "CREATE DATABASE code_knowledge;"
sudo -u postgres psql -c "CREATE USER codebot WITH PASSWORD 'securepass';"

# Redis и Qdrant
docker-compose up -d  # Основные сервисы
docker-compose -f docker-compose.monitoring.yml up -d  # Мониторинг
```

### 3. Инициализация системы
```python
from core.vector_db.qdrant_connector import VectorSearchEngine
engine = VectorSearchEngine()
engine.init_embedder(model_name="google/flan-t5-small")  # Квантованная модель
```

---

## 🔧 Ключевые функции

### 🧠 Семантический анализ кода
```python
from core.analysis.filter import FileFilter
filter = FileFilter()
print(filter.check_relevance("src/auth.py", "auth system"))  # → {"relevance": 0.92}
```

### ⚡️ Управление очередями задач
```bash
rq worker high medium low --with-scheduler  # В отдельном терминале
```

### 🤖 Telegram-интеграция
```bash
echo "TELEGRAM_TOKEN=your_token" > .env
python -m interfaces.telegram.bot_core
```

---

## 📦 Системные компоненты

| Сервис          | Назначение                          | Команда                    |
|-----------------|-------------------------------------|----------------------------|
| **Java-сервис** | Безопасный терминал                | `cd bridges/java/SecureTerminal && mvn package` |
| **C#-сервис**   | Работа с БД                        | `cd bridges/csharp/DatabaseService && dotnet run` |
| **Мониторинг**  | Grafana + Prometheus               | `http://localhost:3000/dashboards` |

---

## 🧪 Тестирование
```bash
# Все тесты одной командой
pytest tests/ -v

# Пример вывода:
# ✔ test_basic_setup (3 passed)
# ✔ test_vector_search (89% coverage)
```

---

## 🚨 Устранение неполадок

**Проблема**: Ошибки подключения к Redis  
**Решение**: 
```bash
redis-cli ping  # Проверка доступности
sudo systemctl restart redis
```

**Проблема**: Отсутствие моделей spaCy  
**Решение**:
```bash
python -m spacy download en_core_web_sm
```

---

## 🏗 Примеры интеграций

### Рефакторинг кода
```python
from core.refactor.code_analyzer import CodeRefactorer
refactorer = CodeRefactorer()
result = refactorer.analyze_file("src/auth.py")  # → Список оптимизаций
```

### Работа с VCS
```python
from core.vcs.git_integration import GitManager
manager = GitManager(".")
print(manager.get_changed_files("HEAD~3..HEAD"))  # → Список изменений
```

---

## 📄 Лицензия  
MIT License | Подробности в `LICENSE.md`

[![Code Assistant Demo](https://img.shields.io/badge/Demo-Video-blue)](https://example.com/demo)
``` 

**Ключевые улучшения:**  
1. Визуальная иерархия с эмодзи и таблицами  
2. Логическая группировка функций  
3. Упрощённые команды для быстрого старта  
4. Добавлен раздел устранения неполадок  
5. Интерактивные примеры использования  
6. Чёткое разделение системных компонентов
