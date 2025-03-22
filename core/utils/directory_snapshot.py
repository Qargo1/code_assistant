import os
import json
from pathlib import Path
from datetime import datetime

def get_directory_snapshot(root_dir='.', output_file='directory_snapshot.json'):
    """Создает структурированный слепок файловой системы"""
    
    # Исключаемые элементы
    EXCLUDE = [
        '__pycache__', 
        '.git', 
        '.idea', 
        'venv', 
        '.env',
        'node_modules',
        '*.pyc',
        '*.log',
        '*.tmp',
        '*.swp'
    ]
    
    def should_skip(path: Path) -> bool:
        """Определяет, нужно ли пропустить файл/директорию"""
        if any(pattern in path.name for pattern in EXCLUDE):
            return True
        if any(path.match(pattern) for pattern in EXCLUDE):
            return True
        return False

    def get_file_info(path: Path) -> dict:
        """Собирает информацию о файле/директории"""
        stat = path.stat()
        return {
            'name': path.name,
            'type': 'directory' if path.is_dir() else 'file',
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'permissions': oct(stat.st_mode)[-3:],
            'absolute_path': str(path.absolute())
        }

    def scan_directory(directory: Path) -> list:
        """Рекурсивно сканирует директорию"""
        structure = []
        
        try:
            for entry in directory.iterdir():
                if should_skip(entry):
                    continue
                
                entry_info = get_file_info(entry)
                
                if entry.is_dir():
                    entry_info['children'] = scan_directory(entry)
                
                structure.append(entry_info)
        except PermissionError:
            pass
            
        return structure

    # Основная логика
    root_path = Path(root_dir).resolve()
    snapshot = {
        'root': str(root_path),
        'timestamp': datetime.now().isoformat(),
        'structure': scan_directory(root_path)
    }

    # Сохранение в файл
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"Слепок сохранен в {output_file}")
    return snapshot

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Создает слепок файловой структуры')
    parser.add_argument('-d', '--dir', default='.', help='Директория для сканирования')
    parser.add_argument('-o', '--output', default='directory_snapshot.json', help='Имя выходного файла')
    
    args = parser.parse_args()
    
    get_directory_snapshot(args.dir, args.output)