# bridges/java_terminal.py
import requests

class JavaTerminalBridge:
    def __init__(self):
        self.url = "http://localhost:8080/execute"
    
    def run_command(self, command: str) -> str:
        try:
            response = requests.post(
                self.url,
                json={"command": command},
                timeout=10
            )
            return response.json()["output"]
        except Exception as e:
            return f"Error: {str(e)}"