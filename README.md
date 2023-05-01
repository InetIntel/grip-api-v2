This is a rewrite of the GRIP API as a Python Flask app.

This API conforms to the specifications described at
https://github.com/CAIDA/grip-api/wiki/API-Documentation


Deployment instructions for development
=======================================

1. Create a python virtual environment (install python3-venv first, if
   necessary):
```
    python3 -m venv grip-api-dev
```

2. Activate the virtual environment:

```
     source ./grip-api-dev/bin/activate
```

3. Install dependencies:

```
     pip3 install flask elasticsearch toml requests
```

4. Create a directory called `instance` in the directory where this README
file is located. Inside that directory, create a valid config file with all
of the required config options (see below for more details).

```
    mkdir -p ./instance
    vim ./instance/config.toml
```

5. Start development server:
```
     export FLASK_ENV=development
     flask run
```

You should now have a local server running on `localhost:5000` that you can
issue GET requests to.

Config options
==============

Configuration is written using the TOML format.

There are 5 config options for this API, all of which are required:

 * `ES_NODES`: a list of URIs describing the members of the elasticsearch
               cluster where the GRIP events are stored.
 * `ES_API_KEY_ID`: the ID portion of the API key that will be used to
                    authenticate with elasticsearch when making a query.
 * `ES_API_KEY_SECRET`: the secret portion of the API key that will be used
                        to authenticate with elasticsearch when making a
                        query.
 * `SECRET_KEY`: a random string that flask will use internally for generating
                 session cookies -- can be anything you like.
 * `META_SERVICE`: the URL to query to access the grip-tags-service.

Note that an elasticsearch API key may be provided to you in a base64 encoded
format. You will need to base64 decode the key to get the ID and secret
portions -- the decoded key should look like `<ID>:<secret>`.

Example config:
```
ES_NODES = ["https://esnode1.example.org:9200", "https://esnode2.example.org:9200"]
ES_API_KEY_ID = "VuaCfGcBCdbkQm-e5aOx"
ES_API_KEY_SECRET = "ui2lp2axTNmsyakw9tvNnw"
SECRET_KEY="myverylongsupersecretkey"
META_SERVICE="http://grip-tags.example.org:5000"
```

Code structure
==============

All interactions with ElasticSearch are defined in `app/elastic.py`. If you
are adding new queries to the API, you should add the query building code
in here.

API methods using the "/json/" blueprint are defined in `app/api_json.py`. If
you are adding API endpoints that are going to return JSON objects, you should
define them in this file as well. Make sure that any routes that you define
call `post_process()` on the fetched data to add the copyright before you
return it to the client.
