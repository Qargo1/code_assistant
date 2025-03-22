import spacy
from typing import List
import ast

nlp = spacy.load("en_core_web_sm")

class CodePatternMatcher:
    def __init__(self):
        self.patterns = {
            "security": [
                {"LOWER": {"IN": ["password", "secret", "token"]}},
                {"LOWER": {"IN": ["hardcode", "store", "log"]}}
            ]
        }

    def find_vulnerabilities(self, code: str) -> List[str]:
        """Поиск паттернов уязвимостей"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []
        
        issues = []
        # Поиск хардкодированных секретов
        if any("password" in node.value for node in ast.walk(tree) 
               if isinstance(node, ast.Str)):
            issues.append("Hardcoded credentials detected")
        
        # NLP анализ комментариев
        doc = nlp(code)
        matches = []
        for match_id, start, end in nlp.tokenizer.match(self.patterns["security"]):
            matches.append(doc[start:end].text)
        
        if matches:
            issues.append(f"Suspicious security patterns: {', '.join(matches)}")
        
        return issues