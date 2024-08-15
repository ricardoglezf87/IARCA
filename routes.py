from flask import render_template, request, jsonify, send_from_directory
from model import classify_image, retrain_model
from exif_utils import update_exif_with_label
from image_utils import get_image_to_classify, process_photos
from config import *

def init_routes(app):
    
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
    
    @app.route('/classify/<filename>', methods=['GET'])
    def classify(filename):
        return classify_image(filename)
    
    @app.route('/image/<filename>')
    def image(filename):
        return send_from_directory(classifyPath, filename)
