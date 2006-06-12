
""" xmlhttp support
"""

from pypy.rpython.ootypesystem.bltregistry import BasicExternal
from pypy.rpython.ootypesystem.ootype import String, Signed, StaticMethod, Bool, Void

class XMLHttpRequest(BasicExternal):
    _fields = {
        'readyState' : int
    }
    
    _methods = {
        'open' : ((str, str, bool), None),
        'send__s' : ((str,), None),
        'send__n' : ((), None),
        #'onreadystatechange' : ([], Void),
    }

##class XMLHttpRequest(object):
##    _rpython_hints = {'_suggested_external' : True}
##    def __init__(self):
##        self.readyState = 0
##        
##    def open(self, method, path, flag):
##        pass
##
##    def send(self, sth):
##        pass
##    
##def get_request():
##    return XMLHttpRequest()
##
##def do_nothing():
##    pass
##
##def xmlSetCallback(func, xml):
##    # scheduler call, but we don't want to mess with threads right now
##    if one() == 0:
##        xmlSetCallback(do_nothing, xml)
##    else:
##        func()
##
##xmlSetCallback.suggested_primitive = True
