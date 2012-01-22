from pypy.interpreter import baseobjspace
from pypy.interpreter.error import OperationError


class PyTraceback(baseobjspace.Wrappable):
    """Traceback object

    Public app-level fields:
     * 'tb_frame'
     * 'tb_lasti'
     * 'tb_lineno'
     * 'tb_next'
    """

    def __init__(self, space, frame, lasti, next):
        self.space = space
        self.frame = frame
        self.lasti = lasti
        self.next = next

    def get_lineno(self):
        return offset2lineno(self.frame.pycode, self.lasti)

    def descr_tb_lineno(self, space):
        return space.wrap(self.get_lineno())

    def descr__reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('traceback_new')
        w        = space.wrap

        tup_base = []
        tup_state = [
            w(self.frame),
            w(self.lasti),
            w(self.next),
            ]
        nt = space.newtuple
        return nt([new_inst, nt(tup_base), nt(tup_state)])

    def descr__setstate__(self, space, w_args):
        from pypy.interpreter.pyframe import PyFrame
        args_w = space.unpackiterable(w_args)
        w_frame, w_lasti, w_next = args_w
        self.frame = space.interp_w(PyFrame, w_frame)
        self.lasti = space.int_w(w_lasti)
        self.next = space.interp_w(PyTraceback, w_next, can_be_None=True)

def record_application_traceback(space, operror, frame, last_instruction):
    if frame.pycode.hidden_applevel:
        return
    tb = operror.get_traceback()
    tb = PyTraceback(space, frame, last_instruction, tb)
    operror.set_traceback(tb)

def offset2lineno(c, stopat):
    tab = c.co_lnotab
    line = c.co_firstlineno
    addr = 0
    for i in range(0, len(tab), 2):
        addr = addr + ord(tab[i])
        if addr > stopat:
            break
        line = line + ord(tab[i+1])
    return line

def check_traceback(space, w_tb, msg):
    from pypy.interpreter.typedef import PyTraceback
    tb = space.interpclass_w(w_tb)
    if tb is None or not space.is_true(space.isinstance(tb, 
            space.gettypeobject(PyTraceback.typedef))):
        raise OperationError(space.w_TypeError, space.wrap(msg))
    return tb
