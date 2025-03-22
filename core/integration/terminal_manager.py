import subprocess
import shlex
from typing import Tuple

class TerminalManager:
    def __init__(self):
        self.safe_commands = ["git pull", "npm install", "ls", "pwd"]
        self.user_confirmations = {}

    async def execute_command(self, command: str, user_id: str) -> Tuple[str, bool]:
        if not self._is_command_safe(command):
            return "Command requires approval", False
            
        if self.user_confirmations.get(user_id) == command:
            result = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout + result.stderr, True
        else:
            self.user_confirmations[user_id] = command
            return "Need approval for: " + command, False

    def _is_command_safe(self, command: str) -> bool:
        return any(cmd in command for cmd in self.safe_commands)