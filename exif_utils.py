import piexif
from PIL import Image
from PIL.ExifTags import TAGS
from geopy.geocoders import Nominatim
import os
from datetime import datetime
from config import *

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
        date_parts = date.split(" ")[0].split(":")  # Extract date parts (year, month, day)
        year = date_parts[0]
        month = date_parts[1]
        return year, month
    
    # If DateTime is not available in EXIF data, get file creation and modification date
    file_creation_time = os.path.getctime(file_path)
    file_modification_time = os.path.getmtime(file_path)
    min_time = min(file_creation_time, file_modification_time)
    return datetime.fromtimestamp(min_time).year, datetime.fromtimestamp(min_time).month

def update_exif_with_label(file_image, label):
    image_path = os.path.join(classifyPath, file_image)
    
    with Image.open(image_path) as img:
        if 'exif' in img.info:
            exif_dict = piexif.load(img.info['exif'])
        else:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        
        tag_bytes = label.encode('utf-16le')
        
        exif_dict['0th'][0x9C9E] = tag_bytes

        if 41729 in exif_dict['Exif'] and isinstance(exif_dict['Exif'][41729], int):
            exif_dict['Exif'][41729] = str(exif_dict['Exif'][41729]).encode('utf-8')
        
        exif_bytes = piexif.dump(exif_dict)
        
        img.save(image_path, "jpeg", exif=exif_bytes)
