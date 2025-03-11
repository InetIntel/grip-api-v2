from flask import jsonify, make_response

def handle_exception(message, status_code): 
    return make_response(jsonify(message), status_code)
