# Thread-local storage.

# XXX no thread support yet, so this is easy :-)

class ThreadLocals:
    pass

locals = ThreadLocals()
locals.executioncontext = None


def getlocals():
    return locals
