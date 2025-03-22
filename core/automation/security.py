class SelfModificationGuard:
    SAFE_PATHS = [
        "external/",
        "tests/",
        ".self/knowledge/"
    ]

    def allow_file_access(self, path: str) -> bool:
        """Проверка разрешенных путей для модификаций"""
        return any(path.startswith(p) for p in self.SAFE_PATHS)

    def validate_self_change(self, diff: str) -> bool:
        """Проверка изменений собственного кода"""
        forbidden_patterns = [
            "os.system",
            "subprocess.run",
            "__import__",
            "sys.modules"
        ]
        return not any(p in diff for p in forbidden_patterns)