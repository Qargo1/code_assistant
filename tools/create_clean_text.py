import os
from pathlib import Path


PATH_TO_CLEAN_CODE = "C:/Users/korda/YandexDisk/steelf/SteelF/clean_code"
MERGED_FILENAME = "C:/Users/korda/YandexDisk/steelf/SteelF/merged_code.txt"
SEPARATOR = "\n\n" + "="*50 + "\n"


def merge_cleaned_files(
    input_dir=PATH_TO_CLEAN_CODE, 
    output_file=MERGED_FILENAME, 
    separator=SEPARATOR
    ):
    
    merged_content = []
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.txt'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        merged_content.append(f"{separator}{file}\n{content}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(merged_content))
        
        
if __name__ == "__main__":
    merge_cleaned_files()