from django.conf.urls.defaults import *

urlpatterns = patterns('pypy.translator.js.examples.djangoping.views',
    (r"^ping.js$", "ping_js"),
    (r"^ping/$", "ping"),
    (r"^$", "index"),
)
