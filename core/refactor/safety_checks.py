class CodeSafetyChecker:
    def validate(self, original: str, modified: str) -> bool:
        """Проверка безопасности изменений"""
        checks = [
            self._syntax_check,
            self._behavior_preservation,
            self._performance_check
        ]
        return all(check(original, modified) for check in checks)

    def _syntax_check(self, original: str, modified: str) -> bool:
        try:
            ast.parse(modified)
            return True
        except SyntaxError:
            return False

    def _behavior_preservation(self, original: str, modified: str) -> bool:
        # Упрощенная проверка через тестовые прогоны
        return self._run_tests(modified)

    def _performance_check(self, original: str, modified: str) -> bool:
        # Сравнение времени выполнения
        orig_time = self._benchmark(original)
        new_time = self._benchmark(modified)
        return new_time <= orig_time * 1.1