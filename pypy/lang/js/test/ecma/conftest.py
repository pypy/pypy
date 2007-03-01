import py
from pypy.lang.js.interpreter import *
from pypy.lang.js.jsobj import W_Array, JsBaseExcept
from pypy.lang.js.jsparser import JsSyntaxError
from py.__.test.outcome import Failed, ExceptionFailure
import pypy.lang.js as js

js.jsobj.DEBUG = False

rootdir = py.magic.autopath().dirpath()
exclusionlist = ['shell.js', 'browser.js']

class JSDirectory(py.test.collect.Directory):

    def filefilter(self, path):
        if not py.test.config.option.ecma:
            return False 
        if path.check(file=1):
            return (path.basename not in exclusionlist)  and (path.ext == '.js')

    def join(self, name):
        if not name.endswith('.js'):
            return super(Directory, self).join(name)
        p = self.fspath.join(name)
        if p.check(file=1):
            return JSTestFile(p, parent=self)



class JSTestFile(py.test.collect.Module):
    def init_interp(cls):
        if hasattr(cls, 'interp'):
            return
        cls.interp = Interpreter()
        ctx = cls.interp.global_context
        shellpath = rootdir/'shell.js'
        t = load_source(shellpath.read())
        t.execute(ctx)
    init_interp = classmethod(init_interp)
    
    def __init__(self, fspath, parent=None):
        super(JSTestFile, self).__init__(fspath, parent)
        self.name = fspath.purebasename
        self.fspath = fspath
          
    def run(self):
        if not py.test.config.option.ecma:
            py.test.skip("ECMA tests disabled, run with --ecma")
        if py.test.config.option.collectonly:
            return
        self.init_interp()
        #actually run the file :)
        t = load_source(self.fspath.read())
        try:
            t.execute(self.interp.global_context)
        except JsSyntaxError:
            raise Failed(msg="Syntax Error",excinfo=py.code.ExceptionInfo())
        except JsBaseExcept:
            raise Failed(msg="Javascript Error", excinfo=py.code.ExceptionInfo())
        testcases = self.interp.global_context.resolve_identifier('testcases')
        testcount = testcases.GetValue().Get('length').GetValue().ToNumber()
        self.testcases = testcases
        # result = [str(i) for i in range(len(values))]
        return range(testcount)

    def join(self, number):
        return JSTestItem(number, parent = self)

    def teardown(self):
        self.testcases.PutValue(W_Array(), self.interp.global_context)

class JSTestItem(py.test.collect.Item):        
    def __init__(self, number, parent=None):
        super(JSTestItem, self).__init__(str(number), parent)
        self.number = number
        
    def run(self):
        ctx = JSTestFile.interp.global_context
        r3 = ctx.resolve_identifier('run_test').GetValue()
        w_test_array = ctx.resolve_identifier('testcases').GetValue()
        w_test_number = W_Number(self.number)
        result = r3.Call(ctx=ctx, args=[w_test_number,]).ToNumber()
        if result == 0:
            w_test = w_test_array.Get(str(self.number)).GetValue()
            w_reason = w_test.Get('reason').GetValue()
            raise Failed(msg=w_reason.ToString())
        elif result == -1:
            py.test.skip()

    _handling_traceback = False
    def _getpathlineno(self):
        return self.parent.parent.fspath, 0 

Directory = JSDirectory
