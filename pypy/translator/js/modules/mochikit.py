
""" mochikit wrappers
"""

from pypy.rpython.extfunc import register_external

def createLoggingPane(var):
    pass
register_external(createLoggingPane, args=[bool])

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

def escapeHTML(data):
    return data
register_external(escapeHTML, args=[str], result=str)

def serializeJSON(data):
    pass
register_external(serializeJSON, args=None, result=str)
