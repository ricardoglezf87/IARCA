import os
from PIL import Image
from exif_utils import get_exif_data, get_date_taken, get_geolocation, geocode_location
from file_utils import process_file
from config import *

def get_unlabeled_images(directory):
    unlabeled_images = []
    
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.jpg', '.jpeg')):
            image_path = os.path.join(directory, filename)
            image = Image.open(image_path)
            exif_data = image._getexif()
            
            if not exif_data or 0x9C9E not in exif_data:
                unlabeled_images.append(filename)
    
    return unlabeled_images

def get_image_to_classify():
    image_directory = classifyPath
    unlabeled_images = get_unlabeled_images(image_directory)
    
    if unlabeled_images:
        return unlabeled_images[0]
    else:
        return None

def process_photos(image_filename): 
    dst_directory = orderedPath             
    file_path = os.path.join(classifyPath, image_filename)
    print(f"Procesando: {file_path}") 

    exif_data = get_exif_data(file_path)
    year_taken, month_taken = get_date_taken(exif_data,file_path)                
    geolocation = get_geolocation(exif_data)

    if geolocation:
        city = geocode_location(*geolocation)
        print(f"Encontrada localizacion: {file_path} -  {city}") 
        if year_taken and city:
            print(f"Encontrada fecha: {file_path} - {month_taken}") 
            dst_path = os.path.join(dst_directory, str(year_taken), str(month_taken), city)                        
            process_file(file_path, dst_path, image_filename) 
            return          
                        
    if year_taken:
        print(f"Encontrada fecha: {file_path} - {year_taken} - {month_taken}") 
        dst_path = os.path.join(dst_directory, str(year_taken), str(month_taken))                        
        process_file(file_path, dst_path, image_filename)
    else:
        print(f"No tiene fecha ni geolocalizacion: {file_path}")  
