from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import re

from gradio_client import Client, handle_file
import time
from dotenv import load_dotenv
import os
import threading
import shutil
import requests
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

# ✅ Generate 3D model using Trellis
def generate_3d_from_image(image_path):
    print(f"[Trellis] Sending image to Trellis: {image_path}")
    client = Client("JeffreyXiang/TRELLIS", hf_token= HF_TOKEN)
    client.predict(api_name="/start_session")

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

    video_path = result['video']

    try:
        extract_result = client.predict(
            mesh_simplify=0.5,
            texture_size=512,
            api_name="/extract_glb"
        )
        glb_path = extract_result[1]

        video_filename = os.path.basename(video_path)
        glb_filename = os.path.basename(glb_path)

        video_dest = os.path.join(UPLOAD_FOLDER, video_filename)
        glb_dest = os.path.join(UPLOAD_FOLDER, glb_filename)

        shutil.copy(video_path, video_dest)
        shutil.copy(glb_path, glb_dest)

        return {
            "video": f"/uploads/{video_filename}",
            "glb": f"/uploads/{glb_filename}"
        }

    except Exception as e:
        print("[⚠️] extract_glb failed:", e)
        return {
            "video": f"/uploads/{os.path.basename(video_path)}",
            "glb": None
        }


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

@app.route('/community')
def community():
    return render_template('community.html', models=uploaded_models)

@app.route('/about')
def about():
    return render_template('about.html', models=uploaded_models)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('model')
        glb_url = request.form.get('glb_url')
        image_url = request.form.get('input_image_url')

        model_name = request.form.get('model_name')
        creator_name = request.form.get('creator_name')
        model_description = request.form.get('model_description')
        prompt_used = request.form.get('prompt_used')
        tags = request.form.get('tags')

        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # ✅ Case 2: Trellis generated a GLB (or a glb_url was passed)
        elif glb_url and glb_url.lower() != "none":
            if glb_url.startswith("/"):
                glb_url = f"http://127.0.0.1:5000{glb_url}"
            filename = os.path.basename(glb_url)
            try:
                r = requests.get(glb_url)
                with open(os.path.join(UPLOAD_FOLDER, filename), 'wb') as f:
                    f.write(r.content)
            except Exception as e:
                print("[⚠️] Failed to fetch GLB:", e)
                filename = None  # fallback if broken

        else:
            print("[⚠️] No GLB file or URL provided.")

        # Save prompt image if provided
        image_filename = None
        if image_url:
            if image_url.startswith("/"):
                image_url = f"http://127.0.0.1:5000{image_url}"
            image_filename = os.path.basename(image_url)
            img_response = requests.get(image_url)
            if img_response.status_code == 200:
                with open(os.path.join(UPLOAD_FOLDER, image_filename), 'wb') as f:
                    f.write(img_response.content)


        slug = re.sub(r'[\W_]+', '-', (model_name or filename).lower()).strip('-')
        uploaded_models.append({
            'slug': slug,
            'name': model_name or filename,
            'path': f'/uploads/{filename}',
            'image': f'/uploads/{image_filename}' if image_filename else None,
            'creator': creator_name,
            'description': model_description or 'No description provided',
            'prompt_used': prompt_used or 'N/A',
            'tags': tags or 'No tags'
        })

        return redirect(url_for('index'))

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
            image.save(image_path)
            time.sleep(0.5)

            try:
                result = generate_3d_from_image(image_path)
                video_url = result['video']
                glb_url = result['glb']

                if glb_url:
                    uploaded_models.append({
                        'slug': re.sub(r'[\W_]+', '-', os.path.basename(glb_url).lower()).strip('-'),
                        'name': os.path.basename(glb_url),
                        'path': glb_url,
                        'description': 'Auto-generated with Trellis',
                        'prompt_used': image.filename,
                        'tags': 'Trellis',
                        'image': f'/uploads/{image.filename}'
                    })

                return render_template('trellis_result.html',
                    video_url=video_url,
                    glb_url=glb_url,
                    model_name=os.path.splitext(image.filename)[0],
                    prompt_used=image.filename,
                    input_image=f"/uploads/{image.filename}"
                )

            except Exception as e:
                print("Trellis Error:", e)
                return render_template('trellis_result.html', error="Trellis failed to generate.")

    return render_template('generate_3d.html')


if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=3000)

