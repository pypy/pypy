import types, sys
from pypy.annotation.model import SomeValue, debugname
from pypy.annotation.annset import AnnotationSet
from pypy.annotation.annrpython import RPythonAnnotator

indent1 = ['']

def show(n):
    if isinstance(n, AnnotationSet):
        return 'heap'
    elif isinstance(n, RPythonAnnotator):
        return 'rpyann'
    else:
        return repr(n)

def trace(o):
    if isinstance(o, types.ClassType):
        for key, value in o.__dict__.items():
            o.__dict__[key] = trace(value)
    elif isinstance(o, types.FunctionType):
        d = {'o': o, 'show': show, 'indent1': indent1, 'stderr': sys.stderr}
        exec """
def %s(*args, **kwds):
    indent, = indent1
    rargs = [show(a) for a in args]
    for kw, value in kwds.items():
        rargs.append('%%s=%%r' %% (kw, value))
    print >> stderr, indent + %r + '(%%s)' %% ', '.join(rargs)
    indent1[0] += '|   '
    try:
        result = o(*args, **kwds)
    except Exception, e:
        indent1[0] = indent
        print >> stderr, indent + '+--> %%s: %%s' %% (e.__class__.__name__, e)
        raise
    indent1[0] = indent
    if result is not None:
        print >> stderr, indent + '+-->', show(result)
    return result
result = %s
""" % (o.__name__, o.__name__, o.__name__) in d
        return d['result']
