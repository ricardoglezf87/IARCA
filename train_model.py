import tensorflow as tf
from tensorflow.keras.applications import MobileNet
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Cargar MobileNet preentrenado
base_model = MobileNet(weights='imagenet', include_top=False, input_shape=(224, 224, 3))

# Congelar las capas del modelo base
base_model.trainable = False

# Añadir nuevas capas para nuestra tarea específica
model = Sequential([
    base_model,
    GlobalAveragePooling2D(),
    Dense(1024, activation='relu'),
    Dense(1, activation='sigmoid')  # Asumiendo una clasificación binaria
])

# Compilar el modelo
model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# Crear un generador de imágenes para el entrenamiento
train_datagen = ImageDataGenerator(rescale=1./255, rotation_range=20, width_shift_range=0.2, height_shift_range=0.2, shear_range=0.2, zoom_range=0.2, horizontal_flip=True, fill_mode='nearest')
train_generator = train_datagen.flow_from_directory(
    'data/images/train',  # Ruta de las imágenes de entrenamiento
    target_size=(224, 224),
    batch_size=32,
    class_mode='binary'
)

# Entrenar el modelo
model.fit(train_generator, epochs=10, steps_per_epoch=100)

# Guardar el modelo
model.save('models/model.h5')
