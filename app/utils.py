from flask import jsonify, make_response

VALID_EVENT_TYPES = ['moas', 'submoas', 'defcon', 'edges']
COPYRIGHT_STRING = "This data is Copyright (c) 2021 Georgia Tech Research Corporation. All Rights Reserved."

def handle_exception(message_str, status_code):
    message = {'error': message_str}
    return make_response(jsonify(message), status_code)

def post_process(data):
    data['copyright'] = COPYRIGHT_STRING
    return jsonify(data)

def validate_event_id(id):
    try: 
        id_split = id.split('-')
    except:
        pass