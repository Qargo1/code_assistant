class ASTTransformer(cst.CSTTransformer):
    def __init__(self, transformations):
        self.transformations = transformations

    def leave_FunctionDef(self, node, updated_node):
        """Применение трансформаций к функциям"""
        for transform in self.transformations.get('functions', []):
            node = transform(node)
        return updated_node

class CodeModifier:
    def apply_transformations(self, code: str, transformations: dict) -> str:
        """Безопасное применение изменений через AST"""
        try:
            tree = cst.parse_module(code)
            modified_tree = tree.visit(ASTTransformer(transformations))
            return modified_tree.code
        except cst.ParserSyntaxError as e:
            raise ValueError(f"Syntax error: {str(e)}")