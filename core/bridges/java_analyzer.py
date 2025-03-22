import jpype
import jpype.imports
from pathlib import Path
import json

class JavaAnalyzer:
    def __init__(self):
        """Initialize Java analysis components using JavaParser."""
        try:
            if not jpype.isJVMStarted():
                jars_path = Path(__file__).parent / "lib" / "javaparser"
                classpath = str(jars_path / "javaparser-core-3.25.5.jar")
                jpype.startJVM(classpath=[classpath])

            # Import Java classes
            from com.github.javaparser import StaticJavaParser
            from com.github.javaparser.ast import CompilationUnit
            from com.github.javaparser.ast.body import ClassOrInterfaceDeclaration, MethodDeclaration

            self.parser = StaticJavaParser
            self._initialized = True
            print("<self>Java analyzer initialized successfully</self>")
        except Exception as e:
            self._initialized = False
            print(f"<error>Failed to initialize Java analyzer: {str(e)}</error>")
            print("<user>Please ensure JavaParser JAR is present in bridges/lib/javaparser/</user>")

    def analyze_file(self, file_path):
        """Analyze a Java source file and return metrics."""
        if not self._initialized:
            raise RuntimeError("Java analyzer not properly initialized")

        try:
            # Parse the file
            compilation_unit = self.parser.parse(Path(file_path))
            
            # Collect metrics
            metrics = self._collect_metrics(compilation_unit)
            print(f"<self>Analysis completed for {file_path}</self>")
            return metrics
        except Exception as e:
            print(f"<error>Analysis failed for {file_path}: {str(e)}</error>")
            raise

    def _collect_metrics(self, compilation_unit):
        """Collect various code metrics from the compilation unit."""
        try:
            metrics = {
                "package": str(compilation_unit.getPackageDeclaration().orElse(None)),
                "imports": [str(imp) for imp in compilation_unit.getImports()],
                "classes": [],
                "interfaces": [],
                "methods": [],
                "complexity": 0
            }

            # Analyze classes and interfaces
            for type_decl in compilation_unit.findAll(jpype.JClass("com.github.javaparser.ast.body.ClassOrInterfaceDeclaration")):
                type_info = {
                    "name": str(type_decl.getNameAsString()),
                    "kind": "interface" if type_decl.isInterface() else "class",
                    "line_start": type_decl.getBegin().get().line,
                    "line_end": type_decl.getEnd().get().line,
                    "methods": [],
                    "fields": []
                }

                # Add fields
                for field in type_decl.getFields():
                    for variable in field.getVariables():
                        field_info = {
                            "name": str(variable.getNameAsString()),
                            "type": str(field.getElementType()),
                            "line": field.getBegin().get().line
                        }
                        type_info["fields"].append(field_info)

                # Add methods
                for method in type_decl.getMethods():
                    method_info = self._analyze_method(method)
                    type_info["methods"].append(method_info)
                    metrics["methods"].append(method_info)
                    metrics["complexity"] += method_info["complexity"]

                if type_info["kind"] == "interface":
                    metrics["interfaces"].append(type_info)
                else:
                    metrics["classes"].append(type_info)

            return metrics
        except Exception as e:
            print(f"<error>Metrics collection failed: {str(e)}</error>")
            raise

    def _analyze_method(self, method):
        """Analyze a method and calculate its metrics."""
        try:
            method_info = {
                "name": str(method.getNameAsString()),
                "return_type": str(method.getType()),
                "parameters": [
                    {
                        "name": str(param.getNameAsString()),
                        "type": str(param.getType())
                    }
                    for param in method.getParameters()
                ],
                "line_start": method.getBegin().get().line,
                "line_end": method.getEnd().get().line,
                "complexity": self._calculate_complexity(method)
            }
            return method_info
        except Exception as e:
            print(f"<error>Method analysis failed: {str(e)}</error>")
            raise

    def _calculate_complexity(self, method):
        """Calculate cyclomatic complexity for a method."""
        try:
            complexity = 1  # Base complexity

            # Count conditional nodes
            complexity += len(method.findAll(jpype.JClass("com.github.javaparser.ast.stmt.IfStmt")))
            complexity += len(method.findAll(jpype.JClass("com.github.javaparser.ast.stmt.WhileStmt")))
            complexity += len(method.findAll(jpype.JClass("com.github.javaparser.ast.stmt.ForStmt")))
            complexity += len(method.findAll(jpype.JClass("com.github.javaparser.ast.stmt.ForEachStmt")))
            complexity += len(method.findAll(jpype.JClass("com.github.javaparser.ast.stmt.CatchClause")))
            complexity += len(method.findAll(jpype.JClass("com.github.javaparser.ast.expr.ConditionalExpr")))

            # Count case statements in switch
            for switch in method.findAll(jpype.JClass("com.github.javaparser.ast.stmt.SwitchStmt")):
                complexity += len(switch.getEntries())

            return complexity
        except Exception as e:
            print(f"<error>Complexity calculation failed: {str(e)}</error>")
            return 1  # Return base complexity on error
