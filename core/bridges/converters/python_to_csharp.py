from tree_sitter import Parser, Language

class PythonToCSharpConverter:
    def __init__(self):
        self.parser = Parser()
        self.parser.set_language(
            Language.build("build/python.so", "python")
        )
        
    def convert(self, python_code: str) -> str:
        """Основная логика конвертации"""
        tree = self.parser.parse(python_code.encode())
        
        # Пример: Конвертация print
        csharp_code = python_code.replace("print(", "Console.WriteLine(")
        
        # Дополнительные правила конвертации
        return self._add_csharp_boilerplate(csharp_code)
    
    def _add_csharp_boilerplate(self, code: str) -> str:
        return f"""
using System;

class Program {{
    static void Main(string[] args) {{
        {code}
    }}
}}
""".strip()