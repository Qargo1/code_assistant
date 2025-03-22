from transformers import AutoTokenizer

def validate_response(response: str) -> bool:
    """Валидация JSON ответа от LLM"""
    try:
        data = json.loads(response)
        return all(key in data for key in ['relevant', 'confidence', 'keywords'])
    except:
        return False

def chunk_content(content: str, token_limit=512) -> list:
    """Разбивка контента на чанки"""
    tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-base")
    tokens = tokenizer.encode(content)
    return [tokenizer.decode(tokens[i:i+token_limit]) 
            for i in range(0, len(tokens), token_limit)]