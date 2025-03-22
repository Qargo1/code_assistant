def test_arch_recommendations():
    advisor = CodeAdvisor()
    recommendations = advisor.generate_recommendations()
    
    assert "architectural" in recommendations
    assert isinstance(recommendations["architectural"], list)

def test_security_analysis():
    matcher = CodePatternMatcher()
    test_code = "password = 'qwerty123'"
    issues = matcher.find_vulnerabilities(test_code)
    
    assert "Hardcoded credentials" in issues[0]