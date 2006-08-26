from django.conf.urls.defaults import *

urlpatterns = patterns('pypy.translator.js.demo.jsdemo.djangoping.views',
    (r"^ping.js$", "ping_js"),
    (r"^ping/$", "ping"),
    (r"^$", "index"),
)
