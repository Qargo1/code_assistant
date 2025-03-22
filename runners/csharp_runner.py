import docker
import tempfile
from pathlib import Path

class CSharpRunner:
    def __init__(self):
        self.client = docker.from_env()
        self.temp_dir = Path("temp/csharp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def run_code(self, code: str, timeout=10) -> dict:
        """Запуск C# кода в Docker-контейнере"""
        with tempfile.NamedTemporaryFile(dir=self.temp_dir, suffix=".cs", delete=False) as f:
            f.write(code.encode())
            file_path = Path(f.name)
            
        try:
            container = self.client.containers.run(
                image="mcr.microsoft.com/dotnet/sdk:7.0",
                command=f"sh -c 'dotnet run {file_path.name}'",
                volumes={str(self.temp_dir): {'bind': '/app', 'mode': 'ro'}},
                working_dir="/app",
                detach=True,
                mem_limit="100m"
            )
            result = container.wait(timeout=timeout)
            logs = container.logs().decode()
            return {
                "success": result["StatusCode"] == 0,
                "output": logs,
                "error": None if result["StatusCode"] == 0 else logs
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            file_path.unlink()