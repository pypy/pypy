# This is only imported for platforms where the built-in faulthandler module is not 
# available.  It provides no function at all so far, but it is enough to start the
# CPython test suite.

def enable(*args, **kwargs):
    pass

def register(*args, **kwargs):
    pass
