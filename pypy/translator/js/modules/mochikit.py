
""" mochikit wrappers
"""

from pypy.rpython.extfunc import genericcallable
from pypy.rpython.extfunc import register_external
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc
from pypy.translator.js.modules import dom

# MochiKit.LoggingPane

def createLoggingPane(var):
    pass
register_external(createLoggingPane, args=[bool])

# MochiKit.Logging

def log(data):
    print data
register_external(log, args=None)

def logDebug(data):
    print "D:", data
register_external(logDebug, args=None)

def logWarning(data):
    print "Warning:", data
register_external(logWarning, args=None)

def logError(data):
    print "ERROR:", data
register_external(logError, args=None)

def logFatal(data):
    print "FATAL:", data
register_external(logFatal, args=None)

# MochiKit.DOM

def escapeHTML(data):
    return data
register_external(escapeHTML, args=[str], result=str)

# MochiKit.Base

def serializeJSON(data):
    pass
register_external(serializeJSON, args=None, result=str)

# MochiKit.Signal

class Event(BasicExternal):
    pass

Event._fields = {
    '_event': dom.Event,
}

Event._methods = {
    'preventDefault': MethodDesc([]),
}


def connect(src, signal, dest):
    print 'connecting signal %s' % (signal,)
register_external(connect, args=[dom.EventTarget, str, genericcallable([Event])],
                  result=int)

def disconnect(id):
    pass
register_external(disconnect, args=[int])

def disconnectAll(src, signal):
    print 'disconnecting all handlers for signal: %s' % (signal,)
register_external(disconnectAll, args=[dom.EventTarget, str])

