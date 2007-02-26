
""" mochikit wrappers
"""

from pypy.rpython.extfunc import register_external

def createLoggingPane(var):
    pass
createLoggingPane.suggested_primitive = True

def log(data):
    pass
log.suggested_primitive = True
log._annspecialcase_ = "specialize:argtype(0)"

def logDebug(data):
    pass
logDebug.suggested_primitive = True
logDebug._annspecialcase_ = "specialize:argtype(0)"

def logWarning(data):
    pass
logWarning.suggested_primitive = True
logWarning._annspecialcase_ = "specialize:argtype(0)"


def logError(data):
    pass
logError.suggested_primitive = True
logError._annspecialcase_ = "specialize:argtype(0)"

def logFatal(data):
    pass
logFatal.suggested_primitive = True
logFatal._annspecialcase_ = "specialize:argtype(0)"

def escapeHTML(data):
    return data
register_external(escapeHTML, args=[str], result=str)

