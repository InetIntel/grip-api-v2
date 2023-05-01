This is a rewrite of the GRIP API as a Python Flask app.

This API conforms to the specifications described at
https://github.com/CAIDA/grip-api/wiki/API-Documentation


Deployment instructions for development
=======================================

1. Create a python virtual environment (install python3-venv first, if
   necessary):
     python3 -m venv grip-api-dev

2. Activate the virtual environment:

     source ./grip-api-dev/bin/activate

3. Install dependencies:

     pip3 install flask elasticsearch toml requests

4. Start development server:

     export FLASK_ENV=development
     flask run

You should now have a local server running on localhost:5000 that you can
issue GET requests to.


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
