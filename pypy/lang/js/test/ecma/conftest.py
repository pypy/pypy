import py
from pypy.lang.js.interpreter import *
from pypy.lang.js.jsobj import W_Array, JsBaseExcept
from pypy.lang.js.jsparser import JsSyntaxError
from py.__.test.outcome import Failed

rootdir = py.magic.autopath().dirpath()
exclusionlist = ['shell.js', 'browser.js']

class JSDirectory(py.test.collect.Directory):

    def filefilter(self, path): 
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
        self.name = fspath.purebasename + " JSFILE"
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
        except (JsBaseExcept, JsSyntaxError):
            raise Failed(excinfo=py.code.ExceptionInfo())
        testcases = self.interp.global_context.resolve_identifier('testcases')
        values = testcases.GetValue().array
        self.testcases = testcases
        result = [str(i) for i in range(len(values))]
        return result

    def join(self, name):
        return JSTestItem(name, parent = self)

    def teardown(self):
        self.testcases.PutValue(W_Array(), self.interp.global_context)

class JSTestItem(py.test.collect.Item):        
    def __init__(self, name, parent=None):
        super(JSTestItem, self).__init__(name, parent)
        self.name = name
        
    def run(self):
        ctx = JSTestFile.interp.global_context
        r3 = ctx.resolve_identifier('run_test').GetValue()
        result = r3.Call(ctx=ctx, args=[W_Number(int(self.name)),]).ToNumber()
        if result == 0:
            py.test.fail()
        elif result == -1:
            py.test.skip()

    _handling_traceback = False
    def _getpathlineno(self):
        return self.parent.parent.fspath, 0 


Directory = JSDirectory
