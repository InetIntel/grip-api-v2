# This source code is Copyright (c) 2023 Georgia Tech Research Corporation. All
# Rights Reserved. Permission to copy, modify, and distribute this software and
# its documentation for academic research and education purposes, without fee,
# and without a written agreement is hereby granted, provided that the above
# copyright notice, this paragraph and the following three paragraphs appear in
# all copies. Permission to make use of this software for other than academic
# research and education purposes may be obtained by contacting:
#
#  Office of Technology Licensing
#  Georgia Institute of Technology
#  926 Dalney Street, NW
#  Atlanta, GA 30318
#  404.385.8066
#  techlicensing@gtrc.gatech.edu
#
# This software program and documentation are copyrighted by Georgia Tech
# Research Corporation (GTRC). The software program and documentation are 
# supplied "as is", without any accompanying services from GTRC. GTRC does
# not warrant that the operation of the program will be uninterrupted or
# error-free. The end-user understands that the program was developed for
# research purposes and is advised not to rely exclusively on the program for
# any reason.
#
# IN NO EVENT SHALL GEORGIA TECH RESEARCH CORPORATION BE LIABLE TO ANY PARTY FOR
# DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING
# LOST PROFITS, ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION,
# EVEN IF GEORGIA TECH RESEARCH CORPORATION HAS BEEN ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE. GEORGIA TECH RESEARCH CORPORATION SPECIFICALLY DISCLAIMS ANY
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE SOFTWARE PROVIDED
# HEREUNDER IS ON AN "AS IS" BASIS, AND  GEORGIA TECH RESEARCH CORPORATION HAS
# NO OBLIGATIONS TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.
#
# This source code is part of the GRIP software. The original GRIP software is
# Copyright (c) 2015 The Regents of the University of California. All rights
# reserved. Permission to copy, modify, and distribute this software for
# academic research and education purposes is subject to the conditions and
# copyright notices in the source code files and in the included LICENSE file.

from ipaddress import ip_network
import elasticsearch
from flask import Blueprint, jsonify, request, current_app
import requests, json

from app.elastic import getElastic
from app.utils import handle_exception
from app.GripException import ValidationError

COPYRIGHT_STRING="This data is Copyright (c) 2021 Georgia Tech Research Corporation. All Rights Reserved."

bp = Blueprint('json', __name__, url_prefix="/json")

def post_process(data):
    data['copyright'] = COPYRIGHT_STRING
    x = jsonify(data)
    return x

@bp.route('/tags', methods=['GET'])
def json_tags():
    r = requests.get(current_app.config['META_SERVICE'] + "/tags")
    data = json.loads(r.content.decode('utf-8'))
    return post_process(data)

@bp.route('/asndrop', methods=['GET'])
def json_asndrop():
    r = requests.get(current_app.config['META_SERVICE'] + "/asndrop")
    data = json.loads(r.content.decode('utf-8'))
    return post_process(data)

@bp.route('/blacklist', methods=['GET'])
def json_blacklist():
    r = requests.get(current_app.config['META_SERVICE'] + "/blacklist")
    data = json.loads(r.content.decode('utf-8'))
    return post_process(data)

@bp.route('/blocklist', methods=['GET'])
def json_blocklist():
    r = requests.get(current_app.config['META_SERVICE'] + "/blacklist")
    data = json.loads(r.content.decode('utf-8'))
    # rename blacklist to blocklist because that's what the caller will expect
    data['blocklist'] = data.pop('blacklist')

    return post_process(data)

@bp.route('/event/id/<evid>', methods=['GET'])
def json_event_by_id(evid):
    try:
        es = getElastic()
        pending = es.getEventById(evid)
        return post_process(pending)

    except elasticsearch.exceptions.NotFoundError:
        return handle_exception('The requested event was not found', 404)
    
    except ValidationError as v:
        return handle_exception(v.args[0], 400)
    
    except Exception as e:
        return handle_exception(e.args[0], 500)

@bp.route('/events', methods=['GET'])
def json_search_events():
    args = request.args

    es = getElastic()

    pending = es.lookupEvents(args)
    return post_process(pending)

@bp.route('/pfx_event/id/<evid>/<prefix>', methods=['GET'])
def json_pfx_event_by_id(evid, prefix):
    try:
        es = getElastic()
        
        fullev = es.getEventById(evid)

        replaced = prefix.replace("-", "/")
        search = replaced.split("_")
        
        for prefix_addr in search:
            # Validating IP addresses, this line will throw a ValueError
            # If IP prefix validation fails
            _ = ip_network(prefix_addr)

        if fullev['event_type'] in ['moas', 'edges']:
            if len(search) != 1:
                err_str = f"{fullev['event_type']} must only have one prefix in the fingerprint for a pfx_event!"
                raise ValidationError(err_str)
            
            for p in fullev['pfx_events']:
                if p['details']['prefix'] == search[0]:
                    return post_process(p)

        elif fullev['event_type'] in ['defcon', 'submoas']:

            if len(search) != 2:
                err_str = f"{fullev['event_type']} must have two prefixes (sub-pfx and super-pfx) in the fingerprint for a pfx_event!"
                raise ValidationError(err_str)
            
            for p in fullev['pfx_events']:
                if p['details']['sub_pfx'] == search[0]:
                    if p['details']['super_pfx'] == search[1]:
                        return post_process(p)

        return handle_exception('No events with the given search parameters were found', 404) # Should this be done, or should we send a 200 with an empty response
    
    except ValidationError as v:
        return handle_exception(v.args[0], 400)

    except elasticsearch.exceptions.NotFoundError:
        return handle_exception('The requested event was not found', 404)

    except ValueError as val:
        return handle_exception("One or more invalid IP prefixes: " + val.args[0], 400)

    except Exception as e:
        return handle_exception(e.args[0], 500)