import py
from pypy.lang.js.interpreter import *
from pypy.lang.js.jsobj import W_Array
from pypy.lang.js.conftest import option

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



class JSTestFile(py.test.collect.Collector):
    def init_interp(cls):
        cls.interp = Interpreter()
        ctx = cls.interp.global_context
        shellpath = rootdir/'shell.js'
        t = load_source(shellpath.read())
        t.execute(ctx)
    init_interp = classmethod(init_interp)
    
    def __init__(self, filepath, parent=None):
        super(JSTestFile, self).__init__(filepath, parent)
        self.name = filepath.purebasename + " JSFILE"
        self.filepath = filepath
    
    def run(self):
        if not option.ecma:
            py.test.skip("ECMA tests disabled, run with --ecma")
        #actually run the file :)
        t = load_source(self.filepath.read())
        try:
            t.execute(self.interp.global_context)
        except:
            py.test.fail("Could not load js file")
        testcases = self.interp.global_context.resolve_identifier('testcases')
        values = testcases.GetValue().array
        testcases.PutValue(W_Array(), self.interp.global_context)
        return values

    def join(self, name):
        return JSTestItem(name, parent = self)

class JSTestItem(py.test.collect.Item):        
    def __init__(self, name, parent=None):
        #super(JSTestItem, self).__init__(filepath, parent)
        self.name = name
         
    def run():
        ctx = JSTestFile.interp.global_context
        r3 = ctx.resolve_identifier('run_test').GetValue()
        result = r3.Call(ctx=ctx, args=[name,]).ToNumber()
        if result == 0:
            py.test.fail()
        elif result == -1:
            py.test.skip()

Directory = JSDirectory
