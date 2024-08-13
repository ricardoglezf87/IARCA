from flask import Flask, render_template, request, jsonify, send_from_directory
import tensorflow as tf
import numpy as np
import os
import piexif
from PIL import Image
from PIL.ExifTags import TAGS

app = Flask(__name__)

categories = ['screenshot', 'meme', 'paisaje', 'animal', 'buceo', 'normal', 'juego']   

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
    
    return jsonify({'message': 'Feedback received and model retrained'})

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
    img = Image.open(image_path)
    
    # Obtener la información EXIF actual o crear un diccionario vacío si no tiene EXIF
    exif_dict = piexif.load(img.info['exif']) if 'exif' in img.info else {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    
    # Obtener las etiquetas actuales en XPKeywords (ID 0x9C9E) si existen
    existing_tags = exif_dict['0th'].get(0x9C9E, b'')
    
    if existing_tags:
        # Decodificar las etiquetas existentes desde UTF-16LE a una cadena
        existing_tags_str = existing_tags.decode('utf-16le').rstrip('\x00')
        # Concatenar la nueva etiqueta a las existentes
        combined_tags = f"{existing_tags_str};{label}"
    else:
        # No hay etiquetas previas, usar la nueva etiqueta como única
        combined_tags = label
    
    # Codificar la nueva lista de etiquetas en UTF-16LE
    tag_bytes = combined_tags.encode('utf-16le')
    
    # Actualizar la etiqueta en XPKeywords (ID 0x9C9E)
    exif_dict['0th'][0x9C9E] = tag_bytes
    
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
