import clr
import os
from pathlib import Path

class CSharpAnalyzer:
    def __init__(self):
        """Initialize C# analysis components using Roslyn."""
        try:
            # Add Roslyn assemblies
            roslyn_path = Path(__file__).parent / "lib" / "roslyn"
            clr.AddReference(str(roslyn_path / "Microsoft.CodeAnalysis.dll"))
            clr.AddReference(str(roslyn_path / "Microsoft.CodeAnalysis.CSharp.dll"))
            
            from Microsoft.CodeAnalysis.CSharp import CSharpSyntaxTree, LanguageVersion
            from Microsoft.CodeAnalysis.CSharp.Syntax import CompilationUnitSyntax
            
            self.syntax_tree = CSharpSyntaxTree
            self.language_version = LanguageVersion
            self._initialized = True
            print("<self>CSharp analyzer initialized successfully</self>")
        except Exception as e:
            self._initialized = False
            print(f"<error>Failed to initialize C# analyzer: {str(e)}</error>")
            print("<user>Please ensure Roslyn assemblies are present in bridges/lib/roslyn/</user>")

    def analyze_file(self, file_path):
        """Analyze a C# source file and return metrics."""
        if not self._initialized:
            raise RuntimeError("C# analyzer not properly initialized")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            # Parse the syntax tree
            tree = self.syntax_tree.ParseText(
                source,
                self.language_version.Latest
            ).GetRoot()

            # Collect metrics
            metrics = self._collect_metrics(tree)
            print(f"<self>Analysis completed for {file_path}</self>")
            return metrics
        except Exception as e:
            print(f"<error>Analysis failed for {file_path}: {str(e)}</error>")
            raise

    def _collect_metrics(self, tree):
        """Collect various code metrics from the syntax tree."""
        try:
            from Microsoft.CodeAnalysis.CSharp.Syntax import (
                ClassDeclarationSyntax,
                MethodDeclarationSyntax,
                PropertyDeclarationSyntax
            )

            metrics = {
                "classes": [],
                "methods": [],
                "properties": [],
                "complexity": 0
            }

            # Analyze classes
            for class_node in tree.DescendantNodes().OfType[ClassDeclarationSyntax]():
                class_info = {
                    "name": class_node.Identifier.Text,
                    "line_start": class_node.GetLocation().GetLineSpan().StartLinePosition.Line + 1,
                    "line_end": class_node.GetLocation().GetLineSpan().EndLinePosition.Line + 1,
                    "methods": [],
                    "properties": []
                }
                metrics["classes"].append(class_info)

                # Analyze methods
                for method in class_node.DescendantNodes().OfType[MethodDeclarationSyntax]():
                    method_info = {
                        "name": method.Identifier.Text,
                        "return_type": method.ReturnType.ToString(),
                        "line_start": method.GetLocation().GetLineSpan().StartLinePosition.Line + 1,
                        "line_end": method.GetLocation().GetLineSpan().EndLinePosition.Line + 1,
                        "complexity": self._calculate_complexity(method)
                    }
                    class_info["methods"].append(method_info)
                    metrics["methods"].append(method_info)
                    metrics["complexity"] += method_info["complexity"]

                # Analyze properties
                for prop in class_node.DescendantNodes().OfType[PropertyDeclarationSyntax]():
                    prop_info = {
                        "name": prop.Identifier.Text,
                        "type": prop.Type.ToString(),
                        "line": prop.GetLocation().GetLineSpan().StartLinePosition.Line + 1
                    }
                    class_info["properties"].append(prop_info)
                    metrics["properties"].append(prop_info)

            return metrics
        except Exception as e:
            print(f"<error>Metrics collection failed: {str(e)}</error>")
            raise

    def _calculate_complexity(self, method_node):
        """Calculate cyclomatic complexity for a method."""
        try:
            complexity = 1  # Base complexity

            # Count branching statements
            complexity += sum(1 for _ in method_node.DescendantNodes().Where(
                lambda n: (
                    n.IsKind(SyntaxKind.IfStatement) or
                    n.IsKind(SyntaxKind.WhileStatement) or
                    n.IsKind(SyntaxKind.ForStatement) or
                    n.IsKind(SyntaxKind.ForEachStatement) or
                    n.IsKind(SyntaxKind.CaseStatement) or
                    n.IsKind(SyntaxKind.CatchClause) or
                    n.IsKind(SyntaxKind.ConditionalExpression)
                )
            ))

            return complexity
        except Exception as e:
            print(f"<error>Complexity calculation failed: {str(e)}</error>")
            return 1  # Return base complexity on error
