import time
from flask import jsonify, make_response

from app.GripException import ValidationError

COPYRIGHT_STRING = "This data is Copyright (c) 2021 Georgia Tech Research Corporation. All Rights Reserved."

def handle_exception(message_str, status_code):
    message = {'error': message_str}
    return make_response(jsonify(message), status_code)

def post_process(data):
    data['copyright'] = COPYRIGHT_STRING
    return jsonify(data)

def is_valid_past_timestamp(timestamp:str):
    timestamp = int(timestamp)
    current_timestamp = int(time.time())
    return 0 < timestamp < current_timestamp
    
def is_valid_asn(asn:str):
    try:
        asn = int(asn)
        isValid = True

        # checking for 32 bit int
        if 1 <= asn <= 4294967295:
            # Checking if private/reserved ASN
            if 64512 <= asn <= 65534 or 4200000000 <= asn <= 4294967295:
                isValid = False
        else:
            isValid = False

        return isValid
    
    except ValueError:
        err_str = "One or more ASNs listed in the event ID are not valid ASNs"
        raise ValidationError(err_str)

def validate_moas(as_list):
    try:
        as_list_arr = as_list.split('_')
        for asn in as_list_arr:
            assert is_valid_asn(asn)  
    
    except Exception as e:
        err_str = "Invalid MOAS event. The right format for a MOAS event is moas-<unix_timestamp>-<asn1_asn2_...>, with each asn being a valid AS number"
        raise ValidationError(err_str)

def validate_submoas(as_list):
    try:
        as_list_arr = as_list.split('=')
        assert len(as_list_arr) == 2
        
        victim_list = as_list_arr[0].split('_')
        for asn in victim_list:
            assert is_valid_asn(asn)
        
        attacker_list = as_list_arr[1].split('_')
        for asn in attacker_list:
            assert is_valid_asn(asn)

    except Exception as e:
        err_str = "Invalid SUBMOAS event. The right format for a SUBMOAS event is submoas-<unix_timestamp>-<victim-asn1_victim-asn2_...>=<attacker-asn1_attacker-asn2...>, with each asn being a valid AS number"
        raise ValidationError(err_str)

def validate_defcon(as_list):
    try:
        as_list_arr = as_list.split('_')
        for asn in as_list_arr:
            assert is_valid_asn(asn)  

    except Exception as e:
        err_str = "Invalid DEFCON event ID. The right format for a DEFCON event is defcon-<unix_timestamp>-<victim-asn1_victim-asn2_...>, with each asn being a valid AS number"
        raise ValidationError(err_str)

def validate_edges(as_list):
    try:
        as_list_arr = as_list.split('_')
        assert len(as_list_arr) == 2
        assert is_valid_asn(as_list_arr[0]) and is_valid_asn(as_list_arr[1])  

    except Exception as e:
        err_str = "Invalid edges event ID. The right format for a edges event is edges-<unix_timestamp>-<asn1_asn2>, with each asn being a valid AS number"
        raise ValidationError(err_str)


def validate_event_id(id):
    try:
        id_split = id.split('-')
        
        if len(id_split) != 3:
            # assuming every event is of the type
            # <eventtype-timestamp-aslist_details>
            err_str = "Invalid event ID"
            raise ValidationError(err_str)
        
        event_type, timestamp, as_details = id_split

        if not is_valid_past_timestamp(timestamp):
            err_str = "Invalid timestamp. Timestamp must be of UNIX timestamp format from the past."
            raise ValidationError(err_str)
        
        event_validation_strategy = {
            'moas': validate_moas,
            'submoas': validate_submoas,
            'defcon': validate_defcon,
            'edges': validate_edges
        }[event_type]

        event_validation_strategy(as_details)

    except KeyError:
        err_str = "Unknown event type. Event type must be one of [ moas, submoas, defcon, edges ]"
        raise ValidationError(err_str)
    
    except Exception as e:
        raise e