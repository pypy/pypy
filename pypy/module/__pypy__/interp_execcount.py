from rpython.rlib import jit
from rpython.rlib import debug
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef

def executioncounter_call(space, w_self, frame, event, w_arg):
    assert isinstance(w_self, W_ExecutionCounter)
    jit.promote(w_self)
    if event == 'return' or event == 'c_return' or event == 'c_exception':
        return
    code = frame.getcode()
    counters = w_self.get_counters(code)
    if frame.last_instr < 0:
        pos = 0
    else:
        pos = frame.last_instr
    assert pos & 1 == 0
    counters[pos // 2] += 1

def saturating_executioncounter_call(space, w_self, frame, event, w_arg):
    assert isinstance(w_self, W_ExecutionCounter)
    jit.promote(w_self)
    if event == 'return' or event == 'c_return' or event == 'c_exception':
        return
    code = frame.getcode()
    if frame.last_instr < 0:
        pos = 0
    else:
        pos = frame.last_instr
    assert pos & 1 == 0
    counter = w_self.saturate_counter(code, pos // 2)
    assert counter != 0


class W_ExecutionCounter(W_Root):
    def __init__(self, space):
        self.counters = {} # pycode -> [counter]
        self.is_enabled = False
        self.space = space

    @jit.elidable
    def get_counters(self, code):
        res = self.counters.get(code)
        if res is None:
            assert len(code.co_code) & 1 == 0
            res = self.counters[code] = [0] * (len(code.co_code) // 2)
            debug.make_sure_not_resized(res)
        return res

    @jit.elidable
    def saturate_counter(self, code, pos):
        self.get_counters(code)[pos] = 1
        return 1

    def enable(self):
        if self.is_enabled:
            return
        self.is_enabled = True
        self.space.getexecutioncontext().setllprofile(executioncounter_call, self)

    def enable_saturating(self):
        if self.is_enabled:
            return
        self.is_enabled = True
        self.space.getexecutioncontext().setllprofile(saturating_executioncounter_call, self)

    def disable(self):
        if not self.is_enabled:
            return
        self.is_enabled = False
        self.space.getexecutioncontext().setllprofile(None, None)

    def getstats(self):
        space = self.space
        w_d = space.newdict()
        for code, counters in self.counters.iteritems():
            space.setitem(w_d, code, space.newlist_int(counters[:]))
        return w_d

def descr_new(space, w_type):
    return W_ExecutionCounter(space)


W_ExecutionCounter.typedef = TypeDef(
    'ExecutionCounter',
    __new__ = interp2app(descr_new),
    enable = interp2app(W_ExecutionCounter.enable),
    enable_saturating = interp2app(W_ExecutionCounter.enable_saturating),
    disable = interp2app(W_ExecutionCounter.disable),
    getstats = interp2app(W_ExecutionCounter.getstats),
)
W_ExecutionCounter.typedef.acceptable_as_base_class = False
