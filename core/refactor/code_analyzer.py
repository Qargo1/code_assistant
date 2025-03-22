import libcst as cst
from typing import Tuple, Dict
from transformers import pipeline
import logging

class CodeRefactorer:
    def __init__(self):
        self.analyzer = pipeline(
            "text-generation",
            model="microsoft/codebert-base",
            device=0 if torch.cuda.is_available() else -1
        )
        self.logger = logging.getLogger(__name__)
        self.safety_check = CodeSafetyChecker()

    def analyze_file(self, file_path: str) -> Dict:
        """Основной метод анализа и рефакторинга"""
        try:
            with open(file_path, "r") as f:
                original_code = f.read()
            
            # Анализ кода
            issues = self._detect_code_smells(original_code)
            
            # Генерация улучшений
            suggestions = self._generate_suggestions(original_code, issues)
            
            # Применение изменений
            refactored_code = self._apply_transformations(original_code, suggestions)
            
            return {
                "original": original_code,
                "refactored": refactored_code,
                "suggestions": suggestions,
                "safe": self.safety_check.validate(original_code, refactored_code)
            }
        except Exception as e:
            self.logger.error(f"Refactor failed: {str(e)}")
            return {"error": str(e)}

    def _detect_code_smells(self, code: str) -> list:
        """Обнаружение проблем в коде"""
        detector = CodeSmellDetector()
        return detector.analyze(code)

    def _generate_suggestions(self, code: str, issues: list) -> list:
        """Генерация предложений через LLM"""
        prompt = self._build_prompt(code, issues)
        response = self.analyzer(prompt, max_length=500)[0]['generated_text']
        return self._parse_response(response)

class CodeSmellDetector:
    def analyze(self, code: str) -> list:
        """Обнаружение стандартных проблем"""
        metrics = self._calculate_metrics(code)
        issues = []
        
        if metrics['cyclomatic'] > 10:
            issues.append("High complexity")
        if metrics['duplication'] > 0.3:
            issues.append("Code duplication")
        
        return issues

    def _calculate_metrics(self, code: str) -> dict:
        """Вычисление метрик кода"""
        # Реализация с использованием radon
        return {...}