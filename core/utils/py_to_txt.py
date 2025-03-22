import os
import re
from pathlib import Path


def process_repository(src_path, dst_path):
    allowed_ext = {'.cs', '.xaml', '.xaml.cs'}
    
    for root, dirs, files in os.walk(src_path):
        # Создаем аналогичную структуру папок
        rel_path = os.path.relpath(root, src_path)
        dest_dir = os.path.join(dst_path, rel_path)
        os.makedirs(dest_dir, exist_ok=True)

        for file in files:
            if Path(file).suffix in allowed_ext:
                process_file(os.path.join(root, file), 
                            os.path.join(dest_dir, file))

def process_file(src_file, dest_file):
    with open(src_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Удаление комментариев
    content = re.sub(r'//.*|/\*[\s\S]*?\*/', '', content)  # C# комментарии
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)  # XAML комментарии
    
    # Удаление region директив
    content = re.sub(r'#region.*?#endregion', '', content, flags=re.DOTALL)
    
    # Упрощение многострочных строковых литералов
    content = re.sub(r'@"[\s\S]*?"', '""', content)
    
    # Сокращение модификаторов доступа
    content = re.sub(r'\b(public|private|protected|internal)\b', '', content)
    
    # Удаление лишних пробелов и пустых строк
    content = '\n'.join([line.strip() for line in content.splitlines() if line.strip()])
    
    # Удаление XML namespaces (для XAML)
    if dest_file.endswith('.xaml'):
        content = re.sub(r'\sxmlns(:?\w+)?="[^"]+"', '', content)
    
    # Сохранение в TXT с метаданными
    with open(f"{dest_file}.txt", 'w', encoding='utf-8') as f:
        f.write(f"Source: {os.path.basename(src_file)}\n\n")
        f.write(content)
        
        
if __name__ == "__main__":
    source_dir = "prev_code"
    dest_dir = "clean_code"
    
    process_repository(source_dir, dest_dir)
    print(f"Processed {len(list(Path(dest_dir).rglob('*.txt')))} files")