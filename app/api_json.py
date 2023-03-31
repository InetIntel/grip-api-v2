from flask import Blueprint, jsonify, request

from app.elastic import getElastic

COPYRIGHT_STRING="This data is Copyright (c) 2021 Georgia Tech Research Corporation. All Rights Reserved."

bp = Blueprint('json', __name__, url_prefix="/json")

def post_process(data):
    data['copyright'] = COPYRIGHT_STRING
    x = jsonify(data)
    return x

@bp.route('/event/id/<evid>', methods=['GET'])
def json_event_by_id(evid):
    es = getElastic()

    pending = es.getEventById(evid)

    return post_process(pending)

@bp.route('/events', methods=['GET'])
def json_search_events():
    args = request.args

    es = getElastic()

    pending = es.lookupEvents(args)
    return post_process(pending)

@bp.route('/pfx_event/id/<evid>/<prefix>', methods=['GET'])
def json_pfx_event_by_id(evid, prefix):
    es = getElastic()

    fullev = es.getEventById(evid)
    if 'error' in fullev:
        return fullev

    replaced = prefix.replace("-", "/")
    search = replaced.split("_")

    if fullev['event_type'] in ['moas', 'edges']:
        if len(search) != 1:
            return {'error': '{} must only have one prefix in the fingerprint for a pfx_event!'.format(fullev['event_type'])}

        for p in fullev['pfx_events']:
            if p['details']['prefix'] == search[0]:
                return post_process(p)

    elif fullev['event_type'] in ['defcon', 'submoas']:

        if len(search) != 2:
            return {'error': '{} must have two prefixes (sub-pfx and super-pfx) in the fingerprint for a pfx_event!'.format(fullev['event_type'])}

        for p in fullev['pfx_events']:
            if p['details']['sub_pfx'] == search[0]:
                if p['details']['super_pfx'] == search[1]:
                    return post_process(p)

    return {}

