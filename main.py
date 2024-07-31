import os
import shutil
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from geopy.geocoders import Nominatim
import imagehash
import concurrent.futures

src_directory = 'C:\\Users\\rgonzafa\\Desktop\\Prueba'
dst_directory = 'C:\\Users\\rgonzafa\\Desktop\\Mov'

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
                    move_file(file_path, os.path.join(dst_path, "Duplicados", file))
                    return None

    if not duplicate_found:
        move_file(file_path, dst_path)

def is_duplicate(image_path1, image_path2):
    try:
        hash1 = imagehash.average_hash(Image.open(image_path1))
        hash2 = imagehash.average_hash(Image.open(image_path2))
        return hash1 == hash2
    except Exception as e:
        print(f"Error al procesar archivos {image_path1} y {image_path2}: {e}")
        return False

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
            city = address.get('city', '')
            tourism = address.get('tourism', '')
            if tourism:
                return tourism
            else:
                return city
        return None
    except Exception as e:
        print(f"Error geocoding location: {e}")
        return None

def get_date_taken(exif_data, file_path):
    date = exif_data.get('DateTime')
    if date:
        date_parts = date.split(" ")[0].split(":")
        year = date_parts[0]
        month = date_parts[1]
        return year, month

    file_creation_time = os.path.getctime(file_path)
    file_modification_time = os.path.getmtime(file_path)
    min_time = min(file_creation_time, file_modification_time)
    return datetime.fromtimestamp(min_time).year, f'{datetime.fromtimestamp(min_time).month:02d}'

def move_file(src_path, dst_path):
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    shutil.move(src_path, dst_path)

def process_photo(file_path):
    file = os.path.basename(file_path)
    print(f"Procesando: {file_path}")

    exif_data = get_exif_data(file_path)
    year_taken, month_taken = get_date_taken(exif_data, file_path)
    geolocation = get_geolocation(exif_data)

    if geolocation:
        city = geocode_location(*geolocation)
        print(f"Encontrada localizacion: {file_path} -  {city}")
        if year_taken and city:
            print(f"Encontrada fecha: {file_path} - {month_taken}")
            dst_path = os.path.join(dst_directory, str(year_taken), str(month_taken), city)
            process_file(file_path, dst_path, file)
            return

    if year_taken:
        print(f"Encontrada fecha: {file_path} - {year_taken} - {month_taken}")
        dst_path = os.path.join(dst_directory, str(year_taken), str(month_taken))
        process_file(file_path, dst_path, file)
    else:
        print(f"No tiene fecha ni geolocalizacion: {file_path}")

def process_photos():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for root, _, files in os.walk(src_directory):
            for file in files:
                if file.lower().endswith(('jpg', 'jpeg', 'png')):
                    file_path = os.path.join(root, file)
                    futures.append(executor.submit(process_photo, file_path))
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing file: {e}")

process_photos()
