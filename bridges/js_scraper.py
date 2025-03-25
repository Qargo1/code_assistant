"""
Мост для извлечения данных с веб-страниц через headless браузер.
Позволяет получать информацию с сайтов, выполнять JavaScript и взаимодействовать с элементами.
"""

import logging
import os
import json
import tempfile
import subprocess
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class JSScraper:
    """
    Класс для взаимодействия с браузером и извлечения данных с веб-страниц.
    Поддерживает два режима работы:
    1. Через Node.js скрипт с использованием Puppeteer (headless Chrome)
    2. Через requests + BeautifulSoup в качестве облегченной альтернативы
    """
    
    def __init__(self, script_path=None, use_puppeteer=True, timeout=30):
        """
        Инициализация скрапера.
        
        Args:
            script_path: Путь к Node.js скрипту для Puppeteer.
                         Если None, используется значение по умолчанию.
            use_puppeteer: Использовать ли Puppeteer или простой requests.
                           Если Puppeteer недоступен, будет автоматически использован requests.
            timeout: Таймаут ожидания загрузки страницы в секундах.
        """
        self.script_path = script_path or os.path.join(
            Path(__file__).parent.parent,
            "resources", "scraper.js"
        )
        self.use_puppeteer = use_puppeteer
        self.timeout = timeout
        
        # Проверка доступности Node.js и Puppeteer
        if self.use_puppeteer:
            self.node_available = self._check_node_available()
            if not self.node_available:
                logger.warning("Node.js not found, fallback to requests+BeautifulSoup")
                self.use_puppeteer = False
                
        logger.info(f"Initialized JSScraper with mode: {'Puppeteer' if self.use_puppeteer else 'Requests'}")
    
    def _check_node_available(self):
        """Проверка доступности Node.js"""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def scrape(self, url, selector, actions=None):
        """
        Получение данных с веб-страницы.
        
        Args:
            url: URL страницы для загрузки.
            selector: CSS-селектор элементов для извлечения.
            actions: Список действий для выполнения перед извлечением данных.
                     Например: [{"type": "click", "selector": ".btn-primary"},
                              {"type": "wait", "time": 2}]
            
        Returns:
            Строка с результатом в JSON-формате
        """
        logger.info(f"Scraping URL: {url}, selector: {selector}")
        
        if not self._is_valid_url(url):
            return json.dumps({
                "error": True,
                "message": f"Invalid URL: {url}"
            })
        
        if self.use_puppeteer and self.node_available:
            return self._scrape_with_puppeteer(url, selector, actions)
        else:
            return self._scrape_with_requests(url, selector)
    
    def _is_valid_url(self, url):
        """Проверка валидности URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _scrape_with_puppeteer(self, url, selector, actions=None):
        """Получение данных с помощью Puppeteer"""
        try:
            # Создание временного файла для передачи параметров
            fd, params_file = tempfile.mkstemp(suffix='.json')
            os.close(fd)
            
            # Параметры для передачи в Node.js скрипт
            params = {
                "url": url,
                "selector": selector,
                "actions": actions or [],
                "timeout": self.timeout * 1000  # в миллисекундах
            }
            
            with open(params_file, 'w') as f:
                json.dump(params, f)
            
            # Запуск Node.js скрипта
            result = subprocess.run(
                ["node", self.script_path, params_file],
                capture_output=True,
                text=True,
                timeout=self.timeout + 10
            )
            
            # Удаление временного файла
            os.unlink(params_file)
            
            # Обработка результата
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Puppeteer error: {result.stderr}")
                return json.dumps({
                    "error": True,
                    "message": f"Puppeteer error: {result.stderr}"
                })
                
        except subprocess.TimeoutExpired:
            logger.error(f"Scraping timeout for URL: {url}")
            return json.dumps({
                "error": True,
                "message": f"Timeout while scraping URL: {url}"
            })
        except Exception as e:
            logger.exception(f"Error while scraping with Puppeteer: {str(e)}")
            return json.dumps({
                "error": True,
                "message": f"Internal error: {str(e)}"
            })
    
    def _scrape_with_requests(self, url, selector):
        """Получение данных с помощью requests и BeautifulSoup"""
        try:
            # Установка заголовков для имитации браузера
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Отправка запроса
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Парсинг HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            elements = soup.select(selector)
            
            # Сбор данных
            results = []
            for i, element in enumerate(elements):
                results.append({
                    "index": i,
                    "text": element.get_text().strip(),
                    "html": str(element),
                    "attributes": {k: v for k, v in element.attrs.items()}
                })
            
            return json.dumps({
                "error": False,
                "count": len(results),
                "elements": results,
                "url": url,
                "selector": selector
            })
            
        except requests.Timeout:
            logger.error(f"Request timeout for URL: {url}")
            return json.dumps({
                "error": True,
                "message": f"Timeout while fetching URL: {url}"
            })
        except requests.HTTPError as e:
            logger.error(f"HTTP error for URL {url}: {str(e)}")
            return json.dumps({
                "error": True,
                "message": f"HTTP error: {str(e)}",
                "status_code": e.response.status_code if hasattr(e, 'response') else None
            })
        except Exception as e:
            logger.exception(f"Error while scraping with requests: {str(e)}")
            return json.dumps({
                "error": True,
                "message": f"Internal error: {str(e)}"
            })
    
    def download_file(self, url, destination_path):
        """
        Скачивание файла с заданного URL.
        
        Args:
            url: URL файла для скачивания.
            destination_path: Путь, куда сохранить файл.
            
        Returns:
            Словарь с результатом операции
        """
        try:
            # Проверка URL
            if not self._is_valid_url(url):
                return {"success": False, "error": "Invalid URL"}
            
            # Создание директории, если не существует
            os.makedirs(os.path.dirname(os.path.abspath(destination_path)), exist_ok=True)
            
            # Скачивание файла
            response = requests.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Получение имени файла из URL, если не указано
            if os.path.isdir(destination_path):
                filename = url.split('/')[-1]
                if not filename:
                    filename = 'download.bin'
                destination_path = os.path.join(destination_path, filename)
            
            # Сохранение файла
            with open(destination_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return {
                "success": True,
                "path": destination_path,
                "size": os.path.getsize(destination_path),
                "url": url
            }
            
        except Exception as e:
            logger.exception(f"Error downloading file from {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def search_code_examples(self, query, language=None, limit=5):
        """
        Поиск примеров кода по заданному запросу.
        
        Args:
            query: Запрос для поиска.
            language: Язык программирования (опционально).
            limit: Максимальное количество результатов.
            
        Returns:
            Список примеров кода
        """
        # Форматирование запроса
        formatted_query = query.replace(' ', '+')
        if language:
            formatted_query += f"+language:{language}"
        
        # URL для поиска на GitHub
        url = f"https://github.com/search?q={formatted_query}&type=code"
        
        # Получение результатов
        result_json = self.scrape(url, ".code-list-item")
        
        try:
            results = json.loads(result_json)
            if results.get("error", True):
                return []
            
            # Обработка результатов
            code_examples = []
            for i, element in enumerate(results.get("elements", [])[:limit]):
                # Извлечение данных
                code = re.search(r'<td.*?class="blob-code.*?">(.*?)</td>', element["html"], re.DOTALL)
                if code:
                    # Очистка от HTML-тегов
                    code_text = BeautifulSoup(code.group(1), 'html.parser').get_text()
                    
                    # Извлечение имени файла и репозитория
                    repo_match = re.search(r'href="/(.*?/.*?)/blob/', element["html"])
                    file_match = re.search(r'blob/.*?/(.*?)"', element["html"])
                    
                    repo = repo_match.group(1) if repo_match else "unknown"
                    filename = file_match.group(1) if file_match else "unknown"
                    
                    code_examples.append({
                        "code": code_text,
                        "repository": repo,
                        "filename": filename,
                        "url": f"https://github.com/{repo}/blob/master/{filename}",
                        "language": language
                    })
            
            return code_examples
            
        except Exception as e:
            logger.exception(f"Error parsing code examples: {str(e)}")
            return [] 