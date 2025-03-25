"""
Мост для безопасного выполнения команд в терминале через Java-приложение.
Обеспечивает изолированное выполнение команд в отдельной среде.
"""

import logging
import subprocess
import os
import tempfile
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class JavaTerminalBridge:
    """
    Класс для взаимодействия с Java-приложением, обеспечивающим
    безопасное выполнение команд в изолированной среде.
    """
    
    def __init__(self, jar_path=None):
        """
        Инициализация моста.
        
        Args:
            jar_path: Путь к JAR-файлу с Java-приложением.
                      Если None, используется значение по умолчанию.
        """
        self.jar_path = jar_path or os.path.join(
            Path(__file__).parent.parent,
            "resources", "SecureTerminal.jar"
        )
        self.java_path = self._find_java()
        self.temp_dir = tempfile.mkdtemp(prefix="secure_terminal_")
        logger.info(f"Initialized JavaTerminalBridge with temp dir: {self.temp_dir}")
        
    def _find_java(self):
        """Поиск исполняемого файла Java"""
        java_path = "java"  # По умолчанию ищем в PATH
        try:
            # Проверка наличия Java
            subprocess.run(
                [java_path, "-version"], 
                capture_output=True, 
                check=True
            )
            return java_path
        except (subprocess.SubprocessError, FileNotFoundError):
            # Поиск по стандартным путям установки
            java_home = os.environ.get("JAVA_HOME")
            if java_home:
                java_path = os.path.join(java_home, "bin", "java")
                if os.path.exists(java_path):
                    return java_path
            
            logger.warning("Java not found. Terminal bridge will use emulation mode.")
            return None
    
    def run_command(self, command):
        """
        Безопасное выполнение команды в изолированной среде.
        
        Args:
            command: Строка с командой для выполнения
            
        Returns:
            Строка с результатом выполнения команды
        """
        logger.info(f"Running command via Java bridge: {command}")
        
        # Проверка доступности Java
        if not self.java_path or not os.path.exists(self.jar_path):
            logger.warning("Java or JAR file not available, using fallback mode")
            return self._emulate_command(command)
        
        try:
            # Создание временного файла для передачи команды
            cmd_file = os.path.join(self.temp_dir, "command.json")
            with open(cmd_file, "w") as f:
                json.dump({"command": command, "timeout": 30}, f)
            
            # Выполнение Java-приложения
            result = subprocess.run(
                [self.java_path, "-jar", self.jar_path, cmd_file],
                capture_output=True,
                text=True,
                timeout=35  # Немного больше, чем таймаут команды
            )
            
            # Обработка результата
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Command failed: {result.stderr}")
                return f"Error executing command: {result.stderr}"
                
        except Exception as e:
            logger.exception(f"Error running command via Java bridge: {str(e)}")
            return f"Internal error: {str(e)}"
        
    def _emulate_command(self, command):
        """Эмуляция выполнения команды для случаев, когда Java недоступна"""
        logger.info(f"Emulating command: {command}")
        
        # Безопасные команды, которые можно эмулировать
        safe_commands = {
            "date": self._emulate_date,
            "echo": self._emulate_echo,
            "pwd": self._emulate_pwd,
            "ls": self._emulate_ls,
            "help": self._emulate_help,
        }
        
        # Определение команды и аргументов
        parts = command.split()
        cmd = parts[0].lower() if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        
        # Выполнение эмуляции
        if cmd in safe_commands:
            return safe_commands[cmd](args)
        else:
            return f"Command '{cmd}' is not supported in emulation mode."
    
    def _emulate_date(self, args):
        """Эмуляция команды date"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _emulate_echo(self, args):
        """Эмуляция команды echo"""
        return " ".join(args)
    
    def _emulate_pwd(self, args):
        """Эмуляция команды pwd"""
        return os.getcwd()
    
    def _emulate_ls(self, args):
        """Эмуляция команды ls"""
        target_dir = args[0] if args else "."
        try:
            items = os.listdir(target_dir)
            return "\n".join(items)
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    def _emulate_help(self, args):
        """Эмуляция команды help"""
        return (
            "Available commands in emulation mode:\n"
            "- date: Show current date and time\n"
            "- echo [text]: Echo the text\n"
            "- pwd: Show current directory\n"
            "- ls [dir]: List directory contents\n"
            "- help: Show this help"
        ) 