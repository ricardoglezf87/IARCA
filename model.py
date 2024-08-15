import tensorflow as tf
from flask import jsonify
import numpy as np
import os
from config import *

# Cargar el modelo preentrenado
model = tf.keras.models.load_model(modelPath)

def retrain_model(new_feedback_data):
    # Preprocesar los nuevos datos
    images = []
    labels = []
    for image_filename, label in new_feedback_data:
        img_path = os.path.join(classifyPath, image_filename)
        
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
    model.save(modelPath)

def classify_image(filename):
    img_path = os.path.join(classifyPath, filename)
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
