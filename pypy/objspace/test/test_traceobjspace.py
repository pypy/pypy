import autopath
from pypy.tool import testit
from pypy.objspace import trace 
from pypy.interpreter.gateway import app2interp
from pypy.tool import pydis
    
class Test_TraceObjSpace(testit.IntTestCase):
    tspace = None
    
    def setUp(self):
        # XXX hack so we only have one trace space
        if Test_TraceObjSpace.tspace is None:
            newspace = testit.objspace().__class__()
            Test_TraceObjSpace.tspace = trace.create_trace_space(newspace)
        
    def tearDown(self):
        pass

    def perform_trace(self, app_func):
        tspace = self.tspace
        func_gw = app2interp(app_func)
        func = func_gw.get_function(tspace)
        tspace.settrace()
        tspace.call_function(tspace.wrap(func))
        res = tspace.getresult()
        return res 

    def test_traceobjspace_basic(self):
        tspace = self.tspace
        self.assert_(tspace.is_true(tspace.w_builtins))
        #for name, value in vars(self.space).items():
        #    if not name.startswith('_'):
        #        self.assert_(value is getattr(t, name))
        #self.assert_(t.is_true(t.make_standard_globals()))

    def test_simpletrace(self):
        def app_f(): 
            pass
        res = self.perform_trace(app_f)
        disresult = pydis.pydis(app_f)
        self.assertEquals(disresult.bytecodes, list(res.getbytecodes()))

    def test_some_builtin1(self):
        def app_f():
            len([1,2,3,4,5])
        res = self.perform_trace(app_f)
        disresult = pydis.pydis(app_f)
        self.assertEquals(len(disresult.bytecodes), len(list(res.getbytecodes())))

    def test_some_builtin2(self):
        def app_f(): 
            filter(None, []) # filter implemented in appspace -> has many more bytecodes        
        res = self.perform_trace(app_f)
        disresult = pydis.pydis(app_f)
        self.failUnless(len(disresult.bytecodes) < len(list(res.getbytecodes())))

    def get_operation(self, iter, optype, name):
        for op in iter:
            if isinstance(op, optype):
                if op.callinfo.name == name:
                    return op
                
    def test_trace_oneop(self):
        def app_f(): 
            1 + 1
        res = self.perform_trace(app_f)
        disresult = pydis.pydis(app_f)
        uw = self.tspace.unwrap
        ops = res.getoperations()
        op_start = self.get_operation(ops, trace.CallBegin, "add")
        args = [uw(x) for x in op_start.callinfo.args]
        self.assertEquals(args, [1, 1])
        op_end = self.get_operation(ops, trace.CallFinished, "add")        
        self.assertEquals(uw(op_end.res), 2)

if __name__ == '__main__':
    testit.main()
