from flask import Flask, request, abort, jsonify, make_response, redirect
from subprocess import call
import os, re, shutil
import cgi

DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', "/files")
FLASK_HOST = os.environ.get('FLASK_HOST', "0.0.0.0")
FLASK_PORT = int(os.environ.get('FLASK_PORT', "8002"))

app = Flask(__name__)

class InvalidArgument(Exception):
    pass

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)

def sanitizeFilename(filename):
    filename = os.path.normpath(filename) # try to eliminate trickery to confuse us
    slash = re.compile(r'/')
    if re.search(slash, filename):
        return None
    return filename

def rm(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
        return True
    else:
        try:
            os.remove(path)
            return True
        except FileNotFoundError:
            return False

@app.route("/upload", methods=['POST'])
def file_upload():
    multiPartFile = request.environ['X-FILE']
    try:
        headers={'content-type': request.headers['content-type'], "content-length = ": request.headers['content-length']}
        environ={
            'REQUEST_METHOD': 'POST', 
            'QUERY_STRING': '', 
            'CONTENT_TYPE': request.headers['content-type'], 
            'CONTENT_LENGTH': request.headers['content-length']
        }
        
        mpart = open(multiPartFile, 'r')
        parsed = cgi.FieldStorage(fp=mpart, environ=environ)

        if 'file' not in parsed:
            raise InvalidArgument("Expected a 'file' field")
        
        
        if not parsed['file'].filename:
            raise InvalidArgument("Expected a filename in the file field")
        
        full_filename = sanitizeFilename(parsed['file'].filename)
        
        if not full_filename:
            raise InvalidArgument("Invalid filename")
        
        
        with open(DOWNLOAD_DIR +"/"+full_filename, 'wb') as extractedFile:
            while True:
                piece = parsed['file'].file.read(4096)  
                if not piece:
                    break
                extractedFile.write(piece)
                    
        mpart.close()
        
        return "SUCCESS", 200
    finally:
        rm(multiPartFile)
        

if __name__ == '__main__':
    try:
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, threaded=True)
    except Exception as e:
        print(e)
