import sys
from py import test, magic

def raises(ExpectedException, *args, **kwargs):
    """ raise AssertionError, if target code does not raise the expected 
        exception. 
    """
    assert args
    if isinstance(args[0], str):
        expr, = args
        assert isinstance(expr, str)
        frame = sys._getframe(1)
        loc = frame.f_locals.copy()
        loc.update(kwargs)
        #print "raises frame scope: %r" % frame.f_locals
        try:
            eval(magic.dyncode.compile2(expr), frame.f_globals, loc) 
            # XXX didn'T mean f_globals == f_locals something special?
            #     this is destroyed here ... 
        except ExpectedException:
            return sys.exc_info()
        except Exception, e:
            excinfo = sys.exc_info()
        else:
            excinfo = None
        raise test.run.ExceptionFailure(expr=expr, expected=ExpectedException, 
                                   innerexcinfo=excinfo, tbindex = -2)
    else:
        func = args[0]
        assert callable 
        try:
            func(*args[1:], **kwargs)
        except ExpectedException:
            return sys.exc_info()
        except Exception, e:
            excinfo = sys.exc_info()
        else:
            excinfo = None
        k = ", ".join(["%s=%r" % x for x in kwargs.items()])
        if k:
            k = ', ' + k
        expr = '%s(%r%s)' %(func.__name__, args, k)
        raise test.run.ExceptionFailure(expr=args, expected=ExpectedException, 
                                   innerexcinfo=excinfo, tbindex = -2)
