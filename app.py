from flask import Flask, render_template, request, send_file
import os
import io
import shutil
from get_penalties import process_penalties, LOGIN_URL

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Class to handle arguments of the user
class Args:
    def __init__(self, data):
        self.cookie = data.get('cookie') or None
        self.user = data.get('user') or None
        self.password = data.get('password') # Wird in der Logik mit getpass/direkt genutzt
        self.startdatum = data.get('startdatum')
        self.max_pages = int(data.get('max_pages', 20))
        self.with_de = data.get('with_de') == 'on'
    
@app.route('/', methods=['GET'])
def index():
    # Shows Input formular
    return render_template('index.html', login_url=LOGIN_URL)

@app.route('/', methods=['POST'])
def run_script():
    # Process the formular and execute the main logic
    data = request.form
    args = Args(data)
    password = args.password

    