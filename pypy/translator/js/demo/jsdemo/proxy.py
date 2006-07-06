
""" xmlhttp controllers, usefull for testing
"""

import turbogears
import cherrypy
from pypy.translator.js.demo.jsdemo.controllers import Root
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc

# Needed double inheritance for both server job
# and semi-transparent communication proxy
class ProxyRoot(Root, BasicExternal):
    """ Class for running communication tests which are not designed to end
    after single function call
    """
    _render_xmlhttp = True
    
    _methods = {
        'send_result' : MethodDesc((('result', "aa"), ('exc', "aa"), ('callback',(lambda : None))), None)
    }
    
    @turbogears.expose(format="json")
    def return_eight(self):
        return dict(eight = 8)
    
    @turbogears.expose(html="jsdemo.templates.xmlhttp")
    def index(self):
        import time
        return dict(now=time.ctime(), onload=self.jsname, code=self.jssource)

ProxyRootInstance = ProxyRoot()
