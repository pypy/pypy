import _continuation, sys


# ____________________________________________________________
# Exceptions

class GreenletExit(Exception):
    """This special exception does not propagate to the parent greenlet; it
can be used to kill a single greenlet."""

error = _continuation.error

# ____________________________________________________________
# Helper function

def getcurrent():
    "Returns the current greenlet (i.e. the one which called this function)."
    try:
        return _tls.current
    except AttributeError:
        # first call in this thread: current == main
        _green_create_main()
        return _tls.current

# ____________________________________________________________
# The 'greenlet' class

_continulet = _continuation.continulet

class greenlet(_continulet):
    getcurrent = staticmethod(getcurrent)
    error = error
    GreenletExit = GreenletExit
    __main = False
    __started = False

    def __init__(self, run=None, parent=None):
        if run is not None:
            self.run = run
        if parent is None:
            parent = getcurrent()
        self.parent = parent

    def switch(self, *args):
        "Switch execution to this greenlet, optionally passing the values "
        "given as argument(s).  Returns the value passed when switching back."
        return self.__switch(_continulet.switch, args)

    def throw(self, typ=GreenletExit, val=None, tb=None):
        "raise exception in greenlet, return value passed when switching back"
        return self.__switch(_continulet.throw, typ, val, tb)

    def __switch(target, unbound_method, *args):
        current = getcurrent()
        #
        while not target:
            if not target.__started:
                _continulet.__init__(target, _greenlet_start, *args)
                args = ()
                target.__started = True
                break
            # already done, go to the parent instead
            # (NB. infinite loop possible, but unlikely, unless you mess
            # up the 'parent' explicitly.  Good enough, because a Ctrl-C
            # will show that the program is caught in this loop here.)
            target = target.parent
        #
        try:
            if current.__main:
                if target.__main:
                    # switch from main to main
                    if unbound_method == _continulet.throw:
                        raise args[0], args[1], args[2]
                    (args,) = args
                else:
                    # enter from main to target
                    args = unbound_method(target, *args)
            else:
                if target.__main:
                    # leave to go to target=main
                    args = unbound_method(current, *args)
                else:
                    # switch from non-main to non-main
                    args = unbound_method(current, *args, to=target)
        except GreenletExit, e:
            args = (e,)
        finally:
            _tls.current = current
        #
        if len(args) == 1:
            return args[0]
        else:
            return args

    def __nonzero__(self):
        return self.__main or _continulet.is_pending(self)

    @property
    def dead(self):
        return self.__started and not self

    @property
    def gr_frame(self):
        raise NotImplementedError("attribute 'gr_frame' of greenlet objects")

# ____________________________________________________________
# Internal stuff

try:
    from thread import _local
except ImportError:
    class _local(object):    # assume no threads
        pass

_tls = _local()

def _green_create_main():
    # create the main greenlet for this thread
    gmain = greenlet.__new__(greenlet)
    gmain._greenlet__main = True
    gmain._greenlet__started = True
    gmain.parent = None
    _tls.main = gmain
    _tls.current = gmain

def _greenlet_start(greenlet, args):
    _tls.current = greenlet
    try:
        res = greenlet.run(*args)
    finally:
        if greenlet.parent is not _tls.main:
            _continuation.permute(greenlet, greenlet.parent)
    return (res,)
