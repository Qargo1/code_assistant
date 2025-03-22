import networkx as nx
from typing import Dict, List
from core.database.connection import get_session
from core.database.models import FileMetadata
import logging

class CodeKnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.logger = logging.getLogger(__name__)
        self._build_graph()

    def _build_graph(self):
        """Построение графа зависимостей из БД"""
        with get_session() as session:
            for file in session.query(FileMetadata).all():
                self.graph.add_node(file.file_path, type=file.semantic_type)
                for dep in file.dependencies:
                    if dep in self.graph:
                        self.graph.add_edge(file.file_path, dep)

    def find_arch_issues(self) -> List[Dict]:
        """Поиск архитектурных проблем"""
        issues = []
        
        # Циклические зависимости
        cycles = list(nx.simple_cycles(self.graph))
        if cycles:
            issues.append({
                "type": "cyclic_dependency",
                "details": cycles[:3]  # Первые 3 цикла
            })
        
        # Слишком связанные модули
        betweenness = nx.betweenness_centrality(self.graph)
        top_coupled = sorted(betweenness.items(), key=lambda x: -x[1])[:5]
        issues.append({
            "type": "high_coupling",
            "details": top_coupled
        })
        
        return issues

    def suggest_improvements(self) -> List[str]:
        """Генерация рекомендаций"""
        issues = self.find_arch_issues()
        suggestions = []
        
        for issue in issues:
            if issue['type'] == 'cyclic_dependency':
                suggestion = self._handle_cycles(issue['details'])
            elif issue['type'] == 'high_coupling':
                suggestion = self._handle_coupling(issue['details'])
            
            suggestions.extend(suggestion)
        
        return suggestions