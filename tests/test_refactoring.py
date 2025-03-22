def test_code_refactoring():
    test_code = "def calc(a,b): return a+b"
    refactorer = CodeRefactorer()
    result = refactorer.analyze_file(test_code)
    
    assert "refactored" in result
    assert "def calculate" in result['refactored']
    assert result['safe'] is True

def test_safety_checks():
    checker = CodeSafetyChecker()
    valid = checker.validate("print(1)", "print(1)")
    invalid = checker.validate("print(1)", "print(1")
    
    assert valid is True
    assert invalid is False