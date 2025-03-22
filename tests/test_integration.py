def test_web_search():
    search = WebSearchManager()
    results = search.google_search("Python memory management")
    assert len(results) > 0

async def test_terminal_approval():
    term = TerminalManager()
    output, ok = await term.execute_command("rm -rf /", "user123")
    assert not ok
    assert "approval" in output