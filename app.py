from flask import Flask, request, abort, jsonify, make_response, redirect, Response
from subprocess import call
import datetime
import hashlib
import os, re, shutil
import cgi
import mmap

DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', "/files")
FLASK_HOST = os.environ.get('FLASK_HOST', "0.0.0.0")
FLASK_PORT = int(os.environ.get('FLASK_PORT', "8002"))

ACCOUNTS = os.environ.get('ACCOUNTS', "")

for account in ACCOUNTS.split(","):
    directory = DOWNLOAD_DIR + "/" + account
    if not os.path.exists(directory):
        os.makedirs(directory)

app = Flask(__name__)

class InvalidArgument(Exception):
    pass

@app.errorhandler(404)
def not_found(error):
    return Response("<html><h1>Not Found</h1><p>The resource could not be found.</p></html>", status=404, mimetype="text/html")


@app.errorhandler(400)
def bad_request(error):
    return Response("<html><h1>Bad request</h1></html>", status=400, mimetype="text/html")

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


def compute_hash(fname):
    
    h = hashlib.md5()
    
    with open(fname, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)
        h.update(mm)
        mm.close()
        return h.hexdigest()
    

def retrieve_container_stats(container_d, compute_object_hash, get_mtime):
    
    if os.path.isdir(container_d):
        
        for object_f in os.scandir(container_d):
            
            stat = os.stat(object_f.path)
            
            yield (
                object_f.name,
                stat.st_size,
                compute_hash(object_f.path) if compute_object_hash else None,
                datetime.datetime.fromtimestamp(stat.st_mtime) if get_mtime else None
            )

    else:
        raise Exception("No such container dir: " + container_d)


def list_containers_text_plain(account):
    for container in os.scandir(account):
        if container.is_dir():
            yield container.name + '\n'
            
def list_objects_text_plain(container):
    for object_f in os.scandir(container):
        yield object_f + '\n'


def list_containers_xml(account_d, account_name):
    yield '<?xml version="1.0" encoding="UTF-8"?>\n<account name="{}">\n'.format(account_name)
    
    for container in os.scandir(account_d):
        
        if container.is_dir():
        
            total_size = 0
            count = 0
            
            for stat in retrieve_container_stats(container.path, False, False):
                count = count + 1
                total_size = total_size + stat[1]
            
            yield '<container><name>{}</name><count>{}</count><bytes>{}</bytes></container>\n'.format(container.name, count, total_size)
        
    yield "</account>\n"
    

def list_objects_xml(container_d, container_name):
    yield '<?xml version="1.0" encoding="UTF-8"?>\n<container name="{}">\n'.format(container_name)
    
    for stat in retrieve_container_stats(container_d, True, True):
        yield '<object><name>{}</name><hash>{}</hash><bytes>{}</bytes><content_type>application/octet-stream</content_type><last_modified>{}</last_modified></object>\n'.format(stat[0], stat[2], stat[1], stat[3])
        
    yield "</container>\n"


def list_containers_json(account):
    yield '['
    
    first = True
    
    for container in os.scandir(account):
        
        if container.is_dir():
        
            total_size = 0
            count = 0
            
            for stat in retrieve_container_stats(container.path, False, False):
                count = count + 1
                total_size = total_size + stat[1]
            
            yield '{}{{"count": {}, "bytes": {}, "name": "{}"}}'.format('' if first else ', ', count, total_size, container.name)
            first = False
        
    yield "]"
    
def list_objects_json(container_d):
    yield '['
    
    first = True
    
    for stat in retrieve_container_stats(container_d, True, True):
        yield '{}{{"hash": "{}", "last_modified": "{}", "bytes": {}, "name": "{}", "content_type": "application/octet-stream"}}'.format('' if first else ', ', stat[2], stat[3], stat[1], stat[0])
        first = False
        
    yield "]"


#################################################################################
## Account Routes


@app.route("/v1/<account>", methods=['GET'], strict_slashes=False)
def list_containers(account):
    
    account_d = DOWNLOAD_DIR + "/" + account
    
    if os.path.isdir(DOWNLOAD_DIR + "/" + account):
        
        accept = request.accept_mimetypes
                
        if 'application/json' in accept:
            return Response(list_containers_json(account_d), mimetype='application/json')
        elif 'application/xml'in accept:
            return Response(list_containers_xml(account_d, account), mimetype='application/xml')
        else:
            return Response(list_containers_text_plain(account_d), mimetype='text/plain')
    else:
        return Response("<html><h1>Not Found</h1><p>The resource could not be found.</p></html>", status=404, mimetype="text/html")

#################################################################################
## Container Routes

@app.route("/v1/<account>/<container>", methods=['PUT'], strict_slashes=False)
def create_container(account, container):
    
    account_d = DOWNLOAD_DIR + "/" + account
    container_d = account_d + "/" + container
    
    if not os.path.exists(container_d):
        os.makedirs(container_d)
        return Response(status=201, mimetype='text/html')
    else:
        return Response(status=202, mimetype='text/html')

@app.route("/v1/<account>/<container>", methods=['GET'], strict_slashes=False)
def get_container(account, container):
    
    account_d = DOWNLOAD_DIR + "/" + account
    container_d = account_d + "/" + container
    
    if os.path.exists(container_d):
        
        accept = request.accept_mimetypes
        
        if 'application/json' in accept:
            return Response(list_objects_json(container_d), mimetype='application/json')
        elif 'application/xml' in accept:
            return Response(list_objects_xml(container_d, container), mimetype='application/xml')
        else:
            return Response(list_objects_text_plain(account_d), mimetype='text/plain')        

    else:
        return Response("<html><h1>Not Found</h1><p>The resource could not be found.</p></html>", status=404, mimetype="text/html")

@app.route("/v1/<account>/<container>", methods=['DELETE'], strict_slashes=False)
def delete_container(account, container):
    
    account_d = DOWNLOAD_DIR + "/" + account
    container_d = account_d + "/" + container
    
    if os.path.exists(container_d):
        try:
            os.rmdir(container_d)
            return Response(status=204, mimetype='text/html')
        except:
            return Response("<html><h1>Conflict</h1><p>There was a conflict when trying to complete your request.</p></html>", status=409, mimetype='text/html')
    else:
        return Response("<html><h1>Not Found</h1><p>The resource could not be found.</p></html>", status=404, mimetype="text/html")


#################################################################################
## Object Routes

@app.route("/v1/<account>/<container>/<objname>", methods=['PUT'])
def file_upload(account, container, objname):

    # This function doesn't do much for now. But it is a place where
    # in the future we can add book keeping and other things.
    
    body = request.environ['X-FILE']
    
    try:
        dest_d = DOWNLOAD_DIR + "/" + account + "/" + container
        
        if not os.path.exists(dest_d):
            return Response("<html><h1>Not Found</h1><p>The resource could not be found.</p></html>", status=404, mimetype="text/html")
        else:
            try:
                os.link(body, dest_d + "/" + objname)
            except:
                shutil.copyfile(body, dest_d + "/" + objname)
            return Response(status=201, mimetype="text/html")
    finally:
        os.unlink(body)
        
@app.route("/v1/<account>/<container>/<objname>", methods=['DELETE'])
def file_deletion(account, container, objname):
    
    obj_f = DOWNLOAD_DIR + "/" + account + "/" + container + "/" + objname
    
    if not os.path.exists(obj_f):
        return Response("<html><h1>Not Found</h1><p>The resource could not be found.</p></html>", status=404, mimetype="text/html")
    else:
        os.unlink(obj_f)
        return Response(status=204, mimetype="text/html")


if __name__ == '__main__':
    try:
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, threaded=True)
    except Exception as e:
        print(e)
