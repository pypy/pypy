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

    def __init__(self, run=None):
        if run is not None:
            self.run = run

    def switch(self, *args):
        "Switch execution to this greenlet, optionally passing the values "
        "given as argument(s).  Returns the value passed when switching back."
        current = getcurrent()
        target = self
        if not target.is_pending() and not target.__main:
            if not target.__started:
                _continulet.__init__(target, _greenlet_start, args)
                args = None
                target.__started = True
            else:
                # already done, go to main instead... xxx later
                raise error("greenlet execution already finished")
        #
        try:
            if current.__main:
                if target.__main:
                    # switch from main to main
                    pass
                else:
                    # enter from main to target
                    args = _continulet.switch(target, args)
            else:
                if target.__main:
                    # leave to go to target=main
                    args = _continulet.switch(current, args)
                else:
                    # switch from non-main to non-main
                    args = _continulet.switch(current, args, to=target)
        except GreenletExit, e:
            args = (e,)
        finally:
            _tls.current = current
        #
        if len(args) == 1:
            return args[0]
        else:
            return args

    def throw(self, typ=GreenletExit, val=None, tb=None):
        "raise exception in greenlet, return value passed when switching back"
        XXX

    __nonzero__ = _continulet.is_pending

    @property
    def dead(self):
        return self.__started and not self

    @property
    def parent(self):
        # Don't support nesting for now.
        if self.__main:
            return None
        else:
            return _tls.main

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
    _tls.main = gmain
    _tls.current = gmain

def _greenlet_start(greenlet, args):
    _tls.current = greenlet
    res = greenlet.run(*args)
    return (res,)
