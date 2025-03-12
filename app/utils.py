from flask import jsonify, make_response

def handle_exception(message_str, status_code):
    message = {'error': message_str}
    return make_response(jsonify(message), status_code)
