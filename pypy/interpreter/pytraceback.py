from pypy.interpreter import baseobjspace
from pypy.interpreter.error import OperationError

from rpython.tool.error import offset2lineno


class PyTraceback(baseobjspace.W_Root):
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
        return space.newint(self.get_lineno())

    def descr__reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod = space.getbuiltinmodule('_pickle_support')
        mod = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('traceback_new')

        tup_base = []
        tup_state = [
            self.frame,
            space.newint(self.lasti),
            self.next,
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

    def descr__dir__(self, space):
        return space.newlist([space.newtext(n) for n in
            ['tb_frame', 'tb_next', 'tb_lasti', 'tb_lineno']])


def record_application_traceback(space, operror, frame, last_instruction):
    if frame.pycode.hidden_applevel:
        return
    tb = operror.get_traceback()
    tb = PyTraceback(space, frame, last_instruction, tb)
    operror.set_traceback(tb)


def check_traceback(space, w_tb, msg):
    if w_tb is None or not space.isinstance_w(w_tb, space.gettypeobject(PyTraceback.typedef)):
        raise OperationError(space.w_TypeError, space.newtext(msg))
    return w_tb
