from flask import jsonify, make_response

VALID_EVENT_TYPES = ['moas', 'submoas', 'defcon', 'edges']
def handle_exception(message_str, status_code):
    message = {'error': message_str}
    return make_response(jsonify(message), status_code)

def validate_event_id(id):
    try: 
        id_split = id.split('-')
    except:
        pass