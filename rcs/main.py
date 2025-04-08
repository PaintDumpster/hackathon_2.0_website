from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = 'uploads'
# ✅ Load previously uploaded models
uploaded_models = []
for filename in os.listdir(UPLOAD_FOLDER):
    if filename.endswith(".glb"):
        uploaded_models.append({
            'name': filename,
            'path': f'/uploads/{filename}',
        })

@app.route('/')
def index():
    return render_template('index.html', models=uploaded_models)

@app.route('/models', methods=['GET','POST'])
def upload():
    if request.method == 'POST':
        # Handle the file upload here
        file = request.files['model']
        if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            uploaded_models.append({
            'name': filename,
            'path': f'/uploads/{filename}',
            'description': 'Uploaded 3D landmark'
            })
            return redirect(url_for('index'))

    return render_template('models.html')

if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=3000)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
