import os
import shutil
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from geopy.geocoders import Nominatim

# Funciones para trabajar con los metadatos EXIF de las imágenes
def get_exif_data(image_path):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if exif_data:
            return {TAGS.get(tag): value for tag, value in exif_data.items()}
    except Exception as e:
        print(f"Error reading EXIF data: {e}")
    return {}

def get_geolocation(exif_data):
    gps_info = exif_data.get('GPSInfo')
    if gps_info:
        # Extraer latitud y longitud de GPSInfo
        def _convert_to_degrees(value):
            d, m, s = value
            return d + (m / 60.0) + (s / 3600.0)
        
        lat = _convert_to_degrees(gps_info[2]) * (-1 if gps_info[1] == 'S' else 1)
        lon = _convert_to_degrees(gps_info[4]) * (-1 if gps_info[3] == 'W' else 1)
        return lat, lon
    return None

def geocode_location(latitude, longitude):
    try:
        geolocator = Nominatim(user_agent="photo_organizer")
        location = geolocator.reverse((latitude, longitude))
        if location and location.raw.get('address'):       
            address = location.raw['address']
            #print(f"Procesando dirección: {address}") 
            city = address.get('city', '')
            tourim =  address.get('tourism', '')
            if tourim:
                return tourim
            else:
                return city
        return None
    except Exception as e:
        return None

def get_date_taken(exif_data, file_path):
    date = exif_data.get('DateTime')
    if date:
        return date.split(" ")[0].split(":")[0]  # Extract year
    
    # If DateTime is not available in EXIF data, get file creation and modification date
    file_creation_time = os.path.getctime(file_path)
    file_modification_time = os.path.getmtime(file_path)
    min_time = min(file_creation_time, file_modification_time)
    return datetime.fromtimestamp(min_time).year

# Función para mover archivos
def move_file(src_path, dst_path):
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    shutil.move(src_path, dst_path)

# Función principal para procesar fotos
def process_photos(src_directory, dst_directory):
    for root, _, files in os.walk(src_directory):
        for file in files:
            if file.lower().endswith(('jpg', 'jpeg', 'png')):                
                file_path = os.path.join(root, file)
                print(f"Procesando: {file_path}") 

                exif_data = get_exif_data(file_path)
                date_taken = get_date_taken(exif_data,file_path)                
                geolocation = get_geolocation(exif_data)

                if geolocation:
                    city = geocode_location(*geolocation)
                    print(f"Encontrada localizacion: {file_path} -  {city}") 
                    if date_taken and city:
                        print(f"Encontrada fecha: {file_path} - {date_taken}") 
                        dst_path = os.path.join(dst_directory, str(date_taken), city, file)                        
                        move_file(file_path, dst_path) 
                        continue                   
                                  
                if date_taken:
                    print(f"Encontrada fecha: {file_path} - {date_taken}") 
                    dst_path = os.path.join(dst_directory, str(date_taken), file)                        
                    move_file(file_path, dst_path)
                else:
                    print(f"No tiene fecha ni geolocalizacion: {file_path}")
    
           
src_directory = 'C:\\Users\\rgonzafa\\Desktop\\Prueba'
dst_directory = 'C:\\Users\\rgonzafa\\Desktop\\Mov'

process_photos(src_directory, dst_directory)