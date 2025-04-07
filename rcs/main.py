from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/models', methods=['POST'])
def upload():
    if request.method == 'POST':
        # Handle the file upload here
        file = request.files['file']
        if file:
            # Save the file or process it
            filename = file.filename
            file.save(f'uploads/{filename}')
        # For example, save the file to a directory or process it
    return render_template('models.html')

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)