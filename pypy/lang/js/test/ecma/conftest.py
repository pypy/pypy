import py
from pypy.lang.js.interpreter import *
from pypy.lang.js.jsobj import W_Array, JsBaseExcept
from pypy.rlib.parsing.parsing import ParseError
from py.__.test.outcome import Failed, ExceptionFailure
import pypy.lang.js as js
from pypy.lang.js import interpreter

interpreter.TEST = True

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
            cls.testcases.PutValue(W_Array(), cls.interp.global_context)
            cls.tc.PutValue(W_Number(0), cls.interp.global_context)

        cls.interp = Interpreter()
        ctx = cls.interp.global_context
        shellpath = rootdir/'shell.js'
        t = load_file(str(shellpath))
        t.execute(ctx)
        cls.testcases = cls.interp.global_context.resolve_identifier('testcases')
        cls.tc = cls.interp.global_context.resolve_identifier('tc')
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
        t = load_file(str(self.fspath))
        try:
            t.execute(self.interp.global_context)
        except ParseError, e:
            raise Failed(msg=e.nice_error_message(filename=str(self.fspath)), excinfo=None)
        except JsBaseExcept:
            raise Failed(msg="Javascript Error", excinfo=py.code.ExceptionInfo())
        except:
            raise Failed(excinfo=py.code.ExceptionInfo())
        testcases = self.interp.global_context.resolve_identifier('testcases')
        self.tc = self.interp.global_context.resolve_identifier('tc')
        testcount = testcases.GetValue().Get('length').GetValue().ToInt32()
        self.testcases = testcases
        return range(testcount)

    def join(self, number):
        return JSTestItem(number, parent = self)

class JSTestItem(py.test.collect.Item):
    def __init__(self, number, parent=None):
        super(JSTestItem, self).__init__(str(number), parent)
        self.number = number
        
    def run(self):
        ctx = JSTestFile.interp.global_context
        r3 = ctx.resolve_identifier('run_test').GetValue()
        w_test_number = W_Number(self.number)
        result = r3.Call(ctx=ctx, args=[w_test_number,]).GetValue().ToString()
        if result != "passed":
            raise Failed(msg=result)
        elif result == -1:
            py.test.skip()

    _handling_traceback = False
    def _getpathlineno(self):
        return self.parent.parent.fspath, 0 

Directory = JSDirectory
