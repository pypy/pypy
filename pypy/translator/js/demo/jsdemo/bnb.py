
""" xmlhttp controllers, usefull for testing
"""

import turbogears
import cherrypy
from pypy.jsdemo.jsdemo.controllers import Root
from pypy.rpython.ootypesystem.bltregistry import BasicExternal

# Needed double inheritance for both server job
# and semi-transparent communication proxy
class BnbRoot(Root, BasicExternal):
    @turbogears.expose
