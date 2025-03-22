from qdrant_client import QdrantClient
from ollama import chat
from semantic import QdrantCodeSearch
import textwrap

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