from typing import List, Dict
from core.analysis.knowledge_graph import CodeKnowledgeGraph
from core.analysis.pattern_matcher import CodePatternMatcher
from core.vector_db.qdrant_connector import VectorSearchEngine

class CodeAdvisor:
    def __init__(self):
        self.graph = CodeKnowledgeGraph()
        self.matcher = CodePatternMatcher()
        self.vector_db = VectorSearchEngine()
    
    def generate_recommendations(self) -> Dict[str, List]:
        """Генерация всех типов рекомендаций"""
        return {
            "architectural": self.graph.suggest_improvements(),
            "security": self._analyze_security(),
            "best_practices": self._suggest_best_practices()
        }
    
    def _analyze_security(self) -> List[str]:
        """Анализ безопасности через несколько методов"""
        issues = []
        for file in self.graph.graph.nodes():
            with open(file) as f:
                issues += self.matcher.find_vulnerabilities(f.read())
        return list(set(issues))[:5]  # Топ 5 проблем
    
    def _suggest_best_practices(self) -> List[str]:
        """Рекомендации на основе схожих проектов"""
        similar_projects = self.vector_db.search_files("good_practices", top_k=3)
        return [f"Consider approach from: {res['file_path']}" for res in similar_projects]