from flask import Flask, render_template, request, jsonify, send_from_directory
import tensorflow as tf
import numpy as np
import os
import piexif
from PIL import Image
import shutil
from datetime import datetime
from PIL.ExifTags import TAGS
from geopy.geocoders import Nominatim
import imagehash
import uuid

app = Flask(__name__)

categories = ['paisaje', 'animal', 'buceo', 'normal', 'borrosa','descartar']   

# Cargar el modelo preentrenado
model = tf.keras.models.load_model('models/model.keras')

# Ruta para mostrar la página principal con una imagen
@app.route('/')
def index():
    image = get_image_to_classify()
    
    if image is None:
        return render_template('index.html', image=None, message="No hay imágenes para clasificar")
    
    return render_template('index.html', image=image, message=None)

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json
    image_filename = data['image']
    label = data['label']

    update_exif_with_label(image_filename, label)
    
    # Leer solo los datos nuevos de feedback
    new_feedback_data = [(image_filename, label)]
    
    # Reentrenar el modelo con los nuevos datos
    retrain_model(new_feedback_data)

    process_photos(image_filename)
    
    return jsonify({'message': 'Feedback received and model retrained'})


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

# Función para mover archivos
def move_file(src_path, dst_path):
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    shutil.move(src_path, dst_path)



# Función principal para procesar fotos
def process_photos(image_filename): 
    dst_directory = 'data/images/ordered'              
    file_path = os.path.join('data/images/to_classify', image_filename)
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

def is_duplicate(image_path1, image_path2):
    try:
        hash1 = imagehash.average_hash(Image.open(image_path1))
        hash2 = imagehash.average_hash(Image.open(image_path2))
        return hash1 == hash2
    except Exception as e:
        print(f"Error al procesar archivos {image_path1} y {image_path2}: {e}")
        return False

def retrain_model(new_feedback_data):
    # Preprocesar los nuevos datos
    images = []
    labels = []
    for image_filename, label in new_feedback_data:
        img_path = os.path.join('data/images/to_classify', image_filename)
        
        # Verificar si el archivo existe
        if not os.path.exists(img_path):
            print(f"El archivo {img_path} no existe y será omitido.")
            continue
        
        img = tf.keras.preprocessing.image.load_img(img_path, target_size=(224, 224))
        x = tf.keras.preprocessing.image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = tf.keras.applications.mobilenet.preprocess_input(x)
        images.append(x)
        labels.append(categories.index(label))
    
    images = np.vstack(images)
    labels = np.array(labels)
    
    labels = tf.keras.utils.to_categorical(labels, num_classes=len(categories))
    
    # Reentrenar el modelo solo con los nuevos datos
    model.fit(images, labels, epochs=1, batch_size=32, verbose=1)
    
    # Guardar el modelo actualizado
    model.save('models/model.keras')


# Ruta para clasificar una imagen
@app.route('/classify/<filename>', methods=['GET'])
def classify_image(filename):
    # Cargar la imagen
    img_path = os.path.join('data/images/to_classify', filename)
    img = tf.keras.preprocessing.image.load_img(img_path, target_size=(224, 224))
    x = tf.keras.preprocessing.image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = tf.keras.applications.mobilenet.preprocess_input(x)
    
    # Clasificar la imagen
    predictions = model.predict(x)
    predicted_class = np.argmax(predictions, axis=1)[0]
    predicted_label = categories[predicted_class]
    
    return jsonify({
        'filename': filename,
        'prediction': predicted_label,
        'confidence': float(predictions[0][predicted_class])
    })

# Ruta para servir las imágenes
@app.route('/image/<filename>')
def image(filename):
    return send_from_directory('data/images/to_classify', filename)


def update_exif_with_label(file_image, label):
    # Ruta de la imagen
    image_path = os.path.join('data/images/to_classify', file_image)
    
    # Abrir la imagen
    with Image.open(image_path) as img:
        # Obtener la información EXIF actual o crear un diccionario vacío si no tiene EXIF
        if 'exif' in img.info:
            exif_dict = piexif.load(img.info['exif'])
        else:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        
        # Codificar la nueva etiqueta en UTF-16LE
        tag_bytes = label.encode('utf-16le')
        
        # Actualizar la etiqueta en XPKeywords (ID 0x9C9E)
        exif_dict['0th'][0x9C9E] = tag_bytes

        if 41729 in exif_dict['Exif'] and isinstance(exif_dict['Exif'][41729], int):
            exif_dict['Exif'][41729] = str(exif_dict['Exif'][41729]).encode('utf-8')
        
        # Convertir de nuevo el diccionario EXIF a formato binario
        exif_bytes = piexif.dump(exif_dict)
        
        # Guardar la imagen con la nueva información EXIF
        img.save(image_path, "jpeg", exif=exif_bytes)

def get_unlabeled_images(directory):
    unlabeled_images = []
    
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.jpg', '.jpeg')):
            image_path = os.path.join(directory, filename)
            image = Image.open(image_path)
            exif_data = image._getexif()
            
            # Verificar si hay datos EXIF y si existe la etiqueta XPKeywords
            if not exif_data or 0x9C9E not in exif_data:
                unlabeled_images.append(filename)
    
    return unlabeled_images

def get_image_to_classify():
    image_directory = 'data/images/to_classify'
    unlabeled_images = get_unlabeled_images(image_directory)
    
    if unlabeled_images:
        # Selecciona la primera imagen sin etiqueta (o puedes usar algún otro criterio)
        return unlabeled_images[0]
    else:
        return None  # Manejar el caso en que todas las imágenes ya están etiquetadas

if __name__ == "__main__":
    app.run(debug=True)
