from flask import Flask, render_template, request, jsonify, send_from_directory
import tensorflow as tf
import numpy as np
import os

app = Flask(__name__)

categories = ['screenshot', 'meme', 'paisaje', 'animal', 'buceo', 'normal', 'juego']   

# Cargar el modelo preentrenado
model = tf.keras.models.load_model('models/model.keras')

# Ruta para mostrar la página principal con una imagen
@app.route('/')
def index():
    image = select_image()  # Función para seleccionar la imagen a mostrar
    return render_template('index.html', image=image)

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json
    image_filename = data['image']
    label = data['label']
    
    # Guardar feedback en un archivo
    with open('data/feedback.txt', 'a') as f:
        f.write(f"{image_filename},{label}\n")
    
    # Retrain the model with the new data
    retrain_model()

    return jsonify({'message': 'Feedback received and model retrained'})

def retrain_model():
    # Leer feedback.txt para obtener el nuevo conjunto de datos etiquetados
    feedback_data = []
    with open('data/feedback.txt', 'r') as f:
        for line in f:
            image_filename, label = line.strip().split(',')
            feedback_data.append((image_filename, label))
    
    # Preprocesar y etiquetar los datos
    images = []
    labels = []
    for image_filename, label in feedback_data:
        img_path = os.path.join('data/images/to_classify', image_filename)
        img = tf.keras.preprocessing.image.load_img(img_path, target_size=(224, 224))
        x = tf.keras.preprocessing.image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = tf.keras.applications.mobilenet.preprocess_input(x)
        images.append(x)
        labels.append(categories.index(label))  # Donde categories es la lista de categorías
    
    images = np.vstack(images)
    labels = np.array(labels)
    
    # Convertir labels a formato categórico (one-hot encoding)
    labels = tf.keras.utils.to_categorical(labels, num_classes=len(categories))
    
    # Reentrenar el modelo
    model.fit(images, labels, epochs=1, batch_size=32)
    
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

def select_image():
    images = os.listdir('data/images/to_classify')
    if images:
        return np.random.choice(images)
    return None

if __name__ == "__main__":
    app.run(debug=True)
