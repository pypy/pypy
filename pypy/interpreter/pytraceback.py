from pypy.interpreter import baseobjspace


class PyTraceback(baseobjspace.Wrappable):
    """Traceback object

    Public fields:
     * 'tb_frame'
     * 'tb_lasti'
     * 'tb_lineno'
     * 'tb_next'
    """

    def __init__(self, space, frame, lasti, lineno, next):
        self.space = space
        self.frame = frame
        self.lasti = lasti
        self.lineno = lineno
        self.next = next

    def descr__reduce__(self, space):
        raise Exception('traceback pickling is work in progress')
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('traceback_new')
        w        = space.wrap

        tup = [
            w(self.frame),
            w(self.lasti),
            w(self.lineno),
            w(self.next),
            ]

        return space.newtuple([new_inst, space.newtuple(tup)])

def record_application_traceback(space, operror, frame, last_instruction):
    if frame.pycode.hidden_applevel:
        return
    lineno = offset2lineno(frame.pycode, last_instruction)
    tb = operror.application_traceback
    tb = PyTraceback(space, frame, last_instruction, lineno, tb)
    operror.application_traceback = tb

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
