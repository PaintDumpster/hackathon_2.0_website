from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import re

from gradio_client import Client, handle_file

def generate_3d_from_image(image_path):
    print(f"[Trellis] Sending image to Trellis: {image_path}")  # 👈 add this for debug
    client = Client("JeffreyXiang/TRELLIS")
    result = client.predict(
        image=handle_file(image_path),
        multiimages=[],
        seed=0,
        ss_guidance_strength=7.5,
        ss_sampling_steps=12,
        slat_guidance_strength=3,
        slat_sampling_steps=12,
        multiimage_algo="stochastic",
        api_name="/image_to_3d"
    )
    return result

def slugify(name):
    return re.sub(r'[\W_]+', '-', name.lower()).strip('-')

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = 'uploads'
# ✅ Load previously uploaded models
uploaded_models = []
for filename in os.listdir(UPLOAD_FOLDER):
    if filename.endswith(".glb"):
        uploaded_models.append({
            'slug': slugify(filename),
            'name': filename,
            'path': f'/uploads/{filename}',
        })

@app.route('/')
def index():
    return render_template('index.html', models=uploaded_models)

@app.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('model')
        model_name = request.form.get('model_name')
        model_description = request.form.get('model_description')
        prompt_used = request.form.get('prompt_used')
        tags = request.form.get('tags')
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            slug = slugify(model_name or filename)
            uploaded_models.append({
                'slug': slug,
                'name': model_name or filename,  # Use the filename if name is not provided
                'path': f'/uploads/{filename}',
                'description': model_description or 'No description provided',
                'prompt_used': prompt_used or 'N/A',
                'tags': tags or 'No tags',
            })
            return redirect(url_for('index'))
        else: 
            return "No file uploaded", 400

    return render_template('upload.html')

@app.route('/model/<slug>')
def model_detail(slug):
    for model in uploaded_models:
        if model['slug'] == slug:
            return render_template('model_details.html', model=model)
    return "Model not found", 404



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/generate_3d', methods=['GET', 'POST'])
def generate_3d():
    if request.method == 'POST':
        image = request.files.get('image')
        if image:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
            image_path = os.path.normpath(image_path).replace("\\", "/")  # ✅ Fix backslashes
            image.save(image_path)
            # ✅ NEW: Let the OS finish writing the file (important for Windows)
            import time
            time.sleep(0.5)

            print(f"[Trellis] Sending image to Trellis: {image_path}")
            
            try:
                result = generate_3d_from_image(image_path)
                video_url = result['video']  # .mp4 preview

                return render_template('trellis_result.html', video_url=video_url, info="This is a temporary preview. Download your .glb from Trellis directly.")
            except Exception as e:
                print("Trellis Error:", e)
                return render_template('trellis_result.html',
                                    error="Trellis failed to generate. Try again later.")

    return render_template('generate_3d.html')


if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=3000)

