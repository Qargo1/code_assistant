class FileSystemCache(CacheBackend):
    def cleanup(self, max_size=1024*1024*1024):  # 1GB
        total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*'))
        if total_size > max_size:
            # Удаление старых файлов
            files = sorted(self.cache_dir.rglob('*'), key=lambda f: f.stat().st_mtime)
            for f in files[:-1000]:  # Сохраняем 1000 последних
                f.unlink()

import zlib

class CompressedCache(CacheBackend):
    def get(self, key):
        compressed = self.backend.get(key)
        return zlib.decompress(compressed) if compressed else None

    def set(self, key, value, ttl):
        compressed = zlib.compress(value)
        self.backend.set(key, compressed, ttl)

# В core/analysis/filter.py
from core.cache.layered_cache import LayeredCache
from core.cache.redis_adapter import RedisCache
from core.cache.file_cache import FileSystemCache

class FileFilter:
    def __init__(self):
        self.cache = LayeredCache()
        self.cache.add_backend(RedisCache())
        self.cache.add_backend(FileSystemCache())
        
    def check_relevance(self, file_path, question):
        cache_key = f"{file_path}-{question}"
        if cached := self.cache.get(cache_key):
            return json.loads(cached)
        
        # ... логика анализа ...
        self.cache.set(cache_key, json.dumps(result), timedelta(hours=1))
        return result

# В core/queue/priority_queue.py
from monitoring.metrics import CodebaseMetrics

metrics = CodebaseMetrics()

class PriorityAnalysisQueue:
    def add_task(self, file_path, metadata):
        try:
            # ... существующий код ...
            metrics.jobs_processed.inc()
            metrics.files_analyzed.labels(language=lang).inc()

class AnalysisWorker:
    def perform_job(self, job):
        with metrics.job_duration.time():
            # ... выполнение задачи ...

# Добавьте в bot_core.py
async def handle_code_explanation(self, update: Update, file_path: str):
    """Генерация объяснения кода через LLM"""
    try:
        with open(file_path) as f:
            code = f.read()
        
        prompt = f"Explain this code:\n```\n{code[:1000]}\n```"
        explanation = self.llm.generate(prompt)
        
        await update.message.reply_markdown(f"📚 Explanation for {file_path}:\n{explanation}")
    except Exception as e:
        logging.error(f"Explanation failed: {str(e)}")
        await update.message.reply_text("❌ Failed to generate explanation")

from interfaces.telegram.bot_core import CodeAssistantBot
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == "__main__":
    bot = CodeAssistantBot(os.getenv("TELEGRAM_TOKEN"))
    bot.run()

from core.vector_db.qdrant_connector import VectorSearchEngine

# Инициализация
engine = VectorSearchEngine()
engine.init_embedder()

# Добавление файла
with open("src/auth.py") as f:
    content = f.read()
engine.add_file("src/auth.py", content, {"type": "authentication"})

# Поиск
results = engine.search_files("How to implement user login?", top_k=5)
for result in results:
    print(f"File: {result['file_path']} (Score: {result['score']:.2f})")
    
# Пакетное добавление файлов
def add_batch(self, files: List[Tuple[str, str, dict]]):
    from tqdm import tqdm
    with ThreadPoolExecutor() as executor:
        list(tqdm(
            executor.map(lambda x: self.add_file(*x), files),
            total=len(files)
        ))
        
from diskcache import Cache

cache = Cache("embeddings_cache")
@cache.memoize()
def cached_encode(text):
    return engine.embedder.encode(text)

def hybrid_search(self, query: str, keywords: List[str], top_k: int = 5):
    query_vector = self.embedder.encode(query).tolist()
    results = self.client.search(
        query_filter=FieldCondition(
            key="keywords",
            match=MatchAny(any=keywords)
        ),
        query_vector=query_vector,
        limit=top_k
    )
    return process_results(results)

#Добавьте обработку больших файлов через чанкинг:
from core.analysis.llm_utils import chunk_content

from core.queue.priority_queue import PriorityAnalysisQueue

queue_system = PriorityAnalysisQueue()

# Добавление задачи
metadata = {
    'dependencies': ['/src/utils.py'],
    'change_frequency': 0.75,
    'complexity': 0.6
}
job_id = queue_system.add_task("/src/api/auth.py", metadata)
print(f"Job ID: {job_id}")

# Проверка статуса
job = queue_system.high_priority.fetch_job(job_id)
print(f"Job status: {job.get_status()}")

# Перезапуск упавших задач
queue_system.restart_failed_jobs()

from qdrant_client import QdrantClient
from ollama import chat
from semantic import QdrantCodeSearch
import textwrap

from core.database.connection import init_db, get_session
from core.database.models import FileMetadata, SemanticType

# Инициализация БД
init_db()

# Пример добавления записи
session = get_session()

new_file = FileMetadata(
    file_path="/src/api/users.py",
    semantic_type=SemanticType.API,
    dependencies=["/src/database.py", "/src/utils/helpers.py"],
    key_functions=["get_user", "create_user", "update_user"]
)

session.add(new_file)
session.commit()

MERGED_FILENAME = "C:/Users/korda/YandexDisk/steelf/SteelF/merged_code.txt"
OLLAMA_MODEL = "qwen2.5-coder:3b"
CONTEXT_TEMPLATE = """
**Code Context**
{context}

**Question**
{question}

**Answer Guidelines**
1. Be specific about code implementation
2. Reference relevant code sections
3. Provide examples when possible
4. Consider language-specific features ({langs})
"""

class ChatBot:
    def __init__(self):
        self.messages = []
        self.qa_system = QdrantCodeSearch(MERGED_FILENAME)
        try:
            self.qa_system.load_and_index_data()
        except Exception as e:
            print(f"Error initializing QA system: {str(e)}")
            raise

    def _format_context(self, results):
        context = []
        langs = set()
        
        for res in results:
            langs.add(res['lang'])
            context.append(
                f"🔍 **Code Fragment** (Score: {res['score']:.2f}, Lines {res['start_line']}-{res['end_line']})\n"
                f"```{res['lang']}\n{textwrap.shorten(res['text'], width=200)}\n```\n"
                f"📁 Source: {res['source']}"
            )
            
        return '\n\n'.join(context), langs

    def get_context(self, query):
        results = self.qa_system.search_code(query, top_k=5)
        context, langs = self._format_context(results)
        return CONTEXT_TEMPLATE.format(
            context=context,
            question=query,
            langs=", ".join(langs)
        )

    def _update_history(self, role, content):
        self.messages.append({'role': role, 'content': content})
        if len(self.messages) > 10:  # Keep last 10 messages
            self.messages = self.messages[-10:]

    def chat(self):
        print("🚀 Code-Aware Chat Bot Initialized\n")
        print("Type 'exit' to quit\n")
        
        while True:
            try:
                user_input = input("👤 User: ")
                if user_input.lower() == 'exit':
                    break
                
                context = self.get_context(user_input)
                self._update_history('user', user_input)
                
                response = chat(
                    model=OLLAMA_MODEL,
                    messages=[{
                        "role": "system",
                        "content": "You are a senior software engineer helping with code analysis."
                    }] + self.messages[-5:] + [{
                        "role": "user",
                        "content": context
                    }]
                )
                
                answer = response['message']['content']
                self._update_history('assistant', answer)
                print(f"\n🤖 Bot:\n{answer}\n")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {str(e)}")

if __name__ == "__main__":
    try:
        chat_bot = ChatBot()
        chat_bot.chat()
    except Exception as e:
        print(f"Critical error: {str(e)}")