from pypy.conftest import gettestobjspace
from py.test import skip


class BaseAppTestPicklePrerequisites(object):
    OPTIONS = {}
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',), **cls.OPTIONS)
        cls.space = space

    def test_pickle_switch_function(object):
        import _stackless, pickle

        sw = _stackless.coroutine.switch.im_func
        dump = pickle.dumps(sw)
        res = pickle.loads(dump)

        assert res is sw
        assert res.func_code is sw.func_code
        assert res.func_doc is sw.func_doc
        assert res.func_globals is sw.func_globals

    def test_pickle_switch_function_code(object):
        import _stackless, pickle

        sw = _stackless.coroutine.switch.im_func.func_code
        dump = pickle.dumps(sw)
        res = pickle.loads(dump)

        assert res is sw
        
class AppTestPicklePrerequisites(BaseAppTestPicklePrerequisites):
    pass

class AppTestPicklePrerequisitesBuiltinShortcut(BaseAppTestPicklePrerequisites):
    OPTIONS = {"objspace.std.builtinshortcut": True}

class FrameCheck(object):

    def __init__(self, name):
        self.name = name

    def __eq__(self, frame):
        return frame.pycode.co_name == self.name

class BytecodeCheck(object):

    def __init__(self, code, op, arg):
        self.code = code
        self.op = chr(op)+chr(arg & 0xff) + chr(arg >> 8 & 0xff)

    def __eq__(self, pos):
        return self.code[pos-3:pos] == self.op

class BaseTestReconstructFrameChain(object):
    OPTIONS = {}

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',), **cls.OPTIONS)
        cls.space = space

        from pypy.rlib import rstack
        cls.old_resume_state_create = rstack.resume_state_create

        def tr(prevstate, label, *args):
            if prevstate is None:
                prevstate = []
            return prevstate+[(label, args)]
        rstack.resume_state_create = tr

        w_opmap = space.appexec([], """():
        import opcode

        return opcode.opmap
        """)

        opmap = space.unwrap(w_opmap)
        cls.CALL_FUNCTION = opmap['CALL_FUNCTION']
        cls.CALL_FUNCTION_VAR = opmap['CALL_FUNCTION_VAR']
        cls.CALL_METHOD = opmap['CALL_METHOD']

        cls.callmethod = getattr(cls, cls.callmethod_label)

    def teardown_class(cls):
        from pypy.rlib import rstack
        rstack.resume_state_create = cls.old_resume_state_create

    def start(self, w_coro):
        self.i = 0
        self.frame_to_check = w_coro.frame
        w_coro.frame = None # avoid exploding in kill > __del__

    def end(self):
        assert self.i == len(self.frame_to_check)

    def check_entry(self, label, *args):
        frame = self.frame_to_check
        assert frame[self.i] == (label, args)
        self.i += 1

        
    def test_two_frames_simple(self):
        space = self.space

        w_res = space.appexec([], """():
        import _stackless as stackless
        import pickle

        main = stackless.coroutine.getcurrent()
        d = {'main': main}        

        exec \"\"\"
def f():
    g(1)

def g(x):
    main.switch()
\"\"\" in d
        f = d['f']
        g = d['g']

        co = stackless.coroutine()
        co.bind(f)
        co.switch()

        s = pickle.dumps(co)
        co = pickle.loads(s)

        return co, f, g
        """)

        w_co, w_f, w_g = space.fixedview(w_res)

        ec = space.getexecutioncontext()
        fcode = w_f.code.co_code
        gcode = w_g.code.co_code        

        self.start(w_co)
        e = self.check_entry
        e('yield_current_frame_to_caller_1')
        e('coroutine__bind', w_co.costate)
        e('appthunk', w_co.costate)
        # f
        e('execute_frame', FrameCheck('f'), ec)
        e('dispatch', FrameCheck('f'), fcode, ec)
        e('handle_bytecode', FrameCheck('f'), fcode, ec)
        e('dispatch_call', FrameCheck('f'), fcode,
          BytecodeCheck(fcode, self.CALL_FUNCTION, 1), ec)
        e('CALL_FUNCTION', FrameCheck('f'), 1)
        # g
        e('execute_frame', FrameCheck('g'), ec)
        e('dispatch', FrameCheck('g'), gcode, ec)
        e('handle_bytecode', FrameCheck('g'), gcode, ec)
        e('dispatch_call', FrameCheck('g'), gcode,
          BytecodeCheck(gcode, self.callmethod, 0), ec)
        e(self.callmethod_label, FrameCheck('g'), 0)
        e('w_switch', w_co.costate, space)
        e('coroutine_switch', w_co.costate)
        self.end()

    def test_two_frames_stararg(self):
        space = self.space

        w_res = space.appexec([], """():
        import _stackless as stackless
        import pickle
        
        main = stackless.coroutine.getcurrent()
        d = {'main': main}        

        exec \"\"\"        
def f():
    g(4, 3, d=2, *(1,))

def g(a, b, c, d):
    main.switch()
\"\"\" in d
        f = d['f']
        g = d['g']    

        co = stackless.coroutine()
        co.bind(f)
        co.switch()

        s = pickle.dumps(co)
        co = pickle.loads(s)

        return co, f, g
        """)

        w_co, w_f, w_g = space.fixedview(w_res)

        ec = space.getexecutioncontext()
        fcode = w_f.code.co_code
        gcode = w_g.code.co_code        

        self.start(w_co)
        e = self.check_entry
        e('yield_current_frame_to_caller_1')
        e('coroutine__bind', w_co.costate)
        e('appthunk', w_co.costate)
        # f
        e('execute_frame', FrameCheck('f'), ec)
        e('dispatch', FrameCheck('f'), fcode, ec)
        e('handle_bytecode', FrameCheck('f'), fcode, ec)
        e('dispatch_call', FrameCheck('f'), fcode,
          BytecodeCheck(fcode, self.CALL_FUNCTION_VAR, 2+(1<<8)), ec)
        e('call_function', FrameCheck('f'))
        # g
        e('execute_frame', FrameCheck('g'), ec)
        e('dispatch', FrameCheck('g'), gcode, ec)
        e('handle_bytecode', FrameCheck('g'), gcode, ec)
        e('dispatch_call', FrameCheck('g'), gcode,
          BytecodeCheck(gcode, self.callmethod, 0), ec)
        e(self.callmethod_label, FrameCheck('g'), 0)
        e('w_switch', w_co.costate, space)
        e('coroutine_switch', w_co.costate)
        self.end()        
    
    def test_two_frames_method(self):
        space = self.space

        w_res = space.appexec([], """():
        import _stackless as stackless
        import pickle
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        
        main = stackless.coroutine.getcurrent()
        d = {'main': main}        

        exec \"\"\"                
def f():
    a = A()
    a.m(1)

def g(_, x):
    main.switch()

class A(object):
    m = g
\"\"\" in d
        f = d['f']
        g = d['g']
        A = d['A']

        # to make pickling work
        mod.A = A
        A.__module__ = 'mod'

        co = stackless.coroutine()
        co.bind(f)
        co.switch()

        s = pickle.dumps(co)
        co = pickle.loads(s)

        return co, f, g
        """)

        w_co, w_f, w_g = space.fixedview(w_res)

        ec = space.getexecutioncontext()
        fcode = w_f.code.co_code
        gcode = w_g.code.co_code        

        self.start(w_co)
        e = self.check_entry
        e('yield_current_frame_to_caller_1')
        e('coroutine__bind', w_co.costate)
        e('appthunk', w_co.costate)
        # f
        e('execute_frame', FrameCheck('f'), ec)
        e('dispatch', FrameCheck('f'), fcode, ec)
        e('handle_bytecode', FrameCheck('f'), fcode, ec)
        e('dispatch_call', FrameCheck('f'), fcode,
          BytecodeCheck(fcode, self.callmethod, 1), ec)
        e(self.callmethod_label, FrameCheck('f'), 1)
        # g
        e('execute_frame', FrameCheck('g'), ec)
        e('dispatch', FrameCheck('g'), gcode, ec)
        e('handle_bytecode', FrameCheck('g'), gcode, ec)
        e('dispatch_call', FrameCheck('g'), gcode,
          BytecodeCheck(gcode, self.callmethod, 0), ec)
        e(self.callmethod_label, FrameCheck('g'), 0)
        e('w_switch', w_co.costate, space)
        e('coroutine_switch', w_co.costate)
        self.end()

class TestReconstructFrameChain(BaseTestReconstructFrameChain):
    callmethod_label = 'CALL_FUNCTION'

class TestReconstructFrameChain_CALL_METHOD(BaseTestReconstructFrameChain):
    OPTIONS = {"objspace.opcodes.CALL_METHOD": True,
               }

    callmethod_label = 'CALL_METHOD'

                
