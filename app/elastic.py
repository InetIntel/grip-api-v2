from elasticsearch import Elasticsearch
from datetime import datetime

import re, time

from flask import current_app, g, request, jsonify

OLD_TIME_FMT="^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$"
NEW_TIME_FMT="^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"

# convert a time parameter into a standard format
#
# input may be either a number of seconds or milliseconds since the epoch,
# or it can be a rfc3339 formatted string (assuming UTC time zone)
#
# Allowed input formats:
#   - 2020-04-09T23:52
#   - 2020-04-09 23:52:00
#   - 15864763620000
#   - 15864763620
#
# All of the above inputs will be converted into:
#   - 2020-04-09 23:52:00
#
def convert_time_str(ts_str):
    if re.match(NEW_TIME_FMT, ts_str):
        return ts_str

    if re.match(OLD_TIME_FMT, ts_str):
        tsplit=ts_str.split("T")
        if len(tsplit) != 2:
            return None     # impossible
        return "{} {}:00".format(tsplit[0], tsplit[1])


    try:
        intts = int(ts_str)
    except ValueError:
        return None

    if intts > time.time() * 10:
        # almost certainly a millisecond timestamp
        intts = int(intts / 1000.0)

    dt = datetime.utcfromtimestamp(intts)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def add_match_params(must_terms, must_not_terms, termname, paramstring):
    termvals=paramstring.split(",")
    for a in termvals:
        if a[0] == '!' and len(a) > 1:
            must_not_terms.append({ "term": {termname: a[1:] }})
        else:
            must_terms.append({ "term": {termname: a }})

def buildESQuery(queryparams):
    q = {}

    start_ts = queryparams.get('ts_start', type=str)
    end_ts = queryparams.get('ts_end', type=str)
    overlap = queryparams.get('overlap', False, type=bool)

    should_filters = []
    must_filters = []

    if start_ts is not None:
        if overlap:
            # case 1: event start time is after "start_ts"
            should_filters.append(
                { "range":  {
                    "view_ts": {
                        "gte": convert_time_str(start_ts)
                    }
                }}
            )
            # case 2: event start time is before "start_ts" BUT ALSO
            #    either event finish time is after "start_ts" OR
            #    the event is ongoing (i.e. no finish time yet)
            should_filters.append(
                { "bool": {
                    "must": [
                        {
                            "range": {
                                "view_ts": {
                                    "lt": convert_time_str(start_ts)
                                }
                            }
                        },
                        {
                            "bool": {
                                "should": [
                                    {
                                        "range": {
                                             "finished_ts": {
                                                 "gte": convert_time_str(start_ts)
                                             }
                                        }
                                    },
                                    {
                                        "bool": {
                                            "must_not": {
                                                "exists": {
                                                    "field": "finished_ts"
                                                }
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }})
            must_filters.append(
                { "bool": {
                    "should": should_filters
                }})
        else:
            # overlap doesn't matter, just has to start after "start_ts"
            must_filters.append(
                { "range": {
                    "view_ts": {
                        "gte": convert_time_str(start_ts)
                    }
                }})

    if end_ts is not None:
        # start time must be before "end_ts" -- finish time is irrelevant
        must_filters.append(
            { "range": {
                "view_ts": {
                    "lte": convert_time_str(end_ts)
                }
            }})

    filter_term = {
            "bool": {
                "must": must_filters
            }
    }

    must_terms = []
    must_not_terms = []

    must_not_terms.append({ "match": {"position": "FINISHED" } })

    # only return events that we have applied inference to
    must_terms.append({ "exists": {"field": "summary.inference_result.primary_inference"} })

    min_susp = queryparams.get("min_susp", 0, type=int)
    max_susp = queryparams.get("max_susp", 100, type=int)

    must_terms.append( {
            "range": {
                "summary.inference_result.primary_inference.suspicion_level": {
                    "lte": max_susp,
                    "gte": min_susp
                }
            }
    } )

    max_dur = queryparams.get("max_duration", type=int)
    min_dur = queryparams.get("min_duration", type=int)

    # some events will have no duration, so don't insert a duration term
    # unless specifically requested -- otherwise the "no duration" events
    # will be excluded from the search results
    if max_dur is not None or min_dur is not None:
        dur_term = {
            "range": { "duration": { } }
        }

        if max_dur is not None:
            dur_term['range']['duration']['lte'] = max_dur
        if min_dur is not None:
            dur_term['range']['duration']['gte'] = min_dur

        must_terms.append(dur_term)

    pfxstring = queryparams.get("pfxs", type=str)
    if pfxstring is not None:
        add_match_params(must_terms, must_not_terms, "summary.prefixes",
                pfxstring)

    asnstring = queryparams.get("asns", type=str)
    if asnstring is not None:
        add_match_params(must_terms, must_not_terms, "summary.ases", asnstring)

    tagstring = queryparams.get("tags", type=str)
    if tagstring is not None:
        add_match_params(must_terms, must_not_terms, "summary.tags.name",
                tagstring)

    codestring = queryparams.get("codes", type=str)
    if codestring is not None:
        add_match_params(must_terms, must_not_terms,
                "summary.inference_result.inferences.inference_id", codestring);

    return {
        'query': {
            'bool': {
                "must": must_terms,
                "must_not": must_not_terms,
                "filter": filter_term
            }
        }
    }


def remove_extra_pfx_event_detail(pfxevent):
    pfx = {}
    for k, v in pfxevent.items():
         if k in ['tags', 'finished_ts', 'inferences']:
             pfx[k] = v

    if "details" in pfxevent and "prefix" in pfxevent['details']:
        pfx['prefix'] = pfxevent['details']['prefix']
    if "details" in pfxevent and "sub_pfx" in pfxevent['details']:
        pfx['sub_pfx'] = pfxevent['details']['sub_pfx']
    if "details" in pfxevent and "super_pfx" in pfxevent['details']:
        pfx['super_pfx'] = pfxevent['details']['super_pfx']

    return pfx

def remove_extra_event_detail(event):

    ev = {}
    ev['pfx_events'] = []
    for k,v in event.items():
        if k in ['id', 'event_type', 'view_ts', 'finished_ts', 'asinfo',
                 'insert_ts', 'last_modified_ts', 'duration', 'tr_metrics',
                 'event_metrics', 'summary']:
             ev[k] = v
             continue

        if k == 'pfx_events':
            for pfx in v:
                ev['pfx_events'].append(remove_extra_pfx_event_detail(pfx))


    ev['debug'] = {}
    return ev

class ElasticSearchConn(object):
    def __init__(self, nodes, api_key_id, api_key_secret):
        self.es = Elasticsearch(nodes,
                timeout=30, max_retries=5, retry_on_timeout=True,
                use_ssl=True, verify_certs=False, ssl_show_warn=False,
                api_key=(api_key_id, api_key_secret))

        if not self.es.ping():
            raise ValueError("Failed to connect to ElasticSearch")

    def getEventById(self, evid):
        evparams = evid.split('-')
        if len(evparams) != 3:
            return {'error': "Invalid event ID format -- should be <evtype>-<timestamp>-<aslist>"}

        evtype = evparams[0]
        try:
            evts = datetime.fromtimestamp(int(evparams[1]))
            datestr = datetime.strftime(evts, "%Y-%m")
        except:
            return {'error': "Invalid timestamp in event ID -- should be a unix timestamp"}

        indexname = "observatory-v4-events-{}-{}".format(
                evtype, datestr)
        result = self.es.get(index=indexname, id=evid)
        return result['_source']

    def lookupEvents(self, queryparams):

        start = queryparams.get("start", default=0, type=int)
        size = queryparams.get("length", default=100, type=int)
        event_type = queryparams.get("event_type", default="*", type=str)

        if event_type == "all":
            event_type = '*'

        brief = queryparams.get("brief")
        debug = queryparams.get("debug")
        full = queryparams.get("full")

        if debug is not None:
            index = "observatory-v4-test-events-{}-*".format(event_type)
        else:
            index = "observatory-v4-events-{}-*".format(event_type)

        kwargs = {'from': start, 'size': size,
                'sort': "view_ts:desc"}

        if brief is not None:
            kwargs["_source"] = "*_ts,id,summary,event_type"

        querybody = buildESQuery(queryparams)

        results = self.es.search(body=querybody, index=index, params=kwargs)
        ret = {"data": [], "draw": None,
                "recordsFiltered": 0, "recordsTotal": 0}

        # recordsFiltered has never been correct (or at least it is
        # a misnomer), so I'm just setting it to 0 for now and we
        # can figure out how to implement later if necessary
        ret['recordsTotal'] = results['hits']['total']['value']

        for num, doc in enumerate(results['hits']['hits']):
            if full is not None:
                d = doc['_source']
                d['_esid'] = doc['_index']
            else:
                # some event details are not required by the UI and can
                # massively increase the response size, so we'll filter
                # those details out unless the user specifically requests
                # them using the `full` parameter
                d = remove_extra_event_detail(doc['_source'])

            ret['data'].append(d)

        return ret

def getElastic():
    if 'es' not in g:
        g.es = ElasticSearchConn(current_app.config['ES_NODES'],
                current_app.config['ES_API_KEY_ID'],
                current_app.config['ES_API_KEY_SECRET'])
    return g.es
