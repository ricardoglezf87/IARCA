import os
import numpy as np

def select_image(image_dir='data/images'):
    images = os.listdir(image_dir)
    return np.random.choice(images)

def save_feedback(image_path, user_label, feedback_file='data/feedback.txt'):
    with open(feedback_file, 'a') as f:
        f.write(f'{image_path},{user_label}\n')
