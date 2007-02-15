"""Django python views"""

from django.http import HttpResponse
from django.shortcuts import render_to_response

from pypy.translator.js.main import rpython2javascript

import simplejson

from pypy.translator.js.examples.djangoping import client

def render_json_response(data):
    response = HttpResponse(mimetype="application/json")
    # response["Pragma"] = "no-cache"
    # response["Cache-Control"] = "no-cache, must-revalidate"
    # response["Expires"] = "Mon, 26 Jul 1997 05:00:00 GMT"
    simplejson.dump(data, response)
    return response

def json(fn):
    def decorator(*args, **kwargs):
        data = fn(*args, **kwargs)
        return render_json_response(data)
    return decorator

def index(request):
    return render_to_response("index.html", {})

@json
def ping(request):
    ping_str = request.GET["ping_str"]
    return client.ping_handler.ping(ping_str)

def ping_js(request):
    js_src = rpython2javascript(client, ["ping_init"])
    response = HttpResponse(mimetype="text/javascript")
    response.write(js_src)
    return response
