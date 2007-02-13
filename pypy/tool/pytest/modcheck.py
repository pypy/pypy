import py

def skipimporterror(name):
    if not hasimport(name):
        __tracebackhide__ = True
        py.test.skip("cannot import %r module" % (name,))

def hasimport(name):
    try:
        __import__(name)
    except ImportError:
        return False
    else:
        return True
