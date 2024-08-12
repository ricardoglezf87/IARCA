from flask import Flask, render_template, request, jsonify, send_from_directory
import tensorflow as tf
import numpy as np
import os

app = Flask(__name__)

# Cargar el modelo preentrenado
model = tf.keras.models.load_model('models/model.h5')

# Ruta para mostrar la página principal con una imagen
@app.route('/')
def index():
    image = select_image()  # Función para seleccionar la imagen a mostrar
    return render_template('index.html', image=image)

# Ruta para recibir y procesar el feedback del usuario
@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json
    image_path = data['image']
    user_label = data['label']
    
    # Guardar el feedback en un archivo
    save_feedback(image_path, user_label)
    
    return jsonify({"message": "Feedback recibido"})

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
    categories = ['screenshot', 'meme', 'paisajes', 'animales', 'buceo', 'normales', 'juegos']
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

def select_image():
    images = os.listdir('data/images/to_classify')
    if images:
        return np.random.choice(images)
    return None

def save_feedback(image_path, user_label):
    with open('data/feedback.txt', 'a') as f:
        f.write(f'{image_path},{user_label}\n')

if __name__ == "__main__":
    app.run(debug=True)
