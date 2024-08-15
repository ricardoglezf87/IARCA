import os
import shutil
import uuid
import imagehash
from PIL import Image

def process_file(file_path, dst_path, file):
    duplicate_found = False
    print(f"Comprobar duplicado: {dst_path}") 
    for root, _, files in os.walk(dst_path):
        for dfile in files:
            if dfile.lower().endswith(('jpg', 'jpeg', 'png')):                
                dfile_path = os.path.join(root, dfile)
                print(f"Procesando duplicado: {dfile_path}") 
                if is_duplicate(file_path, dfile_path):
                    duplicate_found = True
                    guid = uuid.uuid4()
                    file_extension = os.path.splitext(file_path)[1]
                    new_file_name = f"{guid}{file_extension}"
                    move_file(file_path, os.path.join(dst_path,"Duplicados", new_file_name))
                    return None
            
    if not duplicate_found:
        move_file(file_path, os.path.join(dst_path,file))

def is_duplicate(image_path1, image_path2):
    try:
        hash1 = imagehash.average_hash(Image.open(image_path1))
        hash2 = imagehash.average_hash(Image.open(image_path2))
        return hash1 == hash2
    except Exception as e:
        print(f"Error al procesar archivos {image_path1} y {image_path2}: {e}")
        return False

def move_file(src_path, dst_path):
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    shutil.move(src_path, dst_path)
