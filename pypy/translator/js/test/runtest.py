
import py, os, re, subprocess
from pypy.translator.translator import TranslationContext
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.js.js import JS
from pypy.translator.js.test.browsertest import jstest
from pypy.translator.js import conftest
from pypy.translator.js.log import log
from pypy.conftest import option
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin
from pypy.rlib.nonconst import NonConstant
from pypy.rpython.ootypesystem import ootype

from pypy.rpython.llinterp import LLException

log = log.runtest
use_browsertest = conftest.option.browser
use_tg = conftest.option.tg

port = 8080

class JSException(LLException):
    pass

def _CLI_is_on_path():
    if py.path.local.sysfind('js') is None:  #we recommend Spidermonkey
        return False
    return True

class compile_function(object):
    def __init__(self, function, annotations, stackless=False, view=False, html=None, is_interactive=False, root = None, run_browser = True, policy = None):
        if not use_browsertest and not _CLI_is_on_path():
            py.test.skip('Javascript CLI (js) not found')

        self.html = html
        self.is_interactive = is_interactive
        t = TranslationContext()
        
        if policy is None:
            from pypy.annotation.policy import AnnotatorPolicy
            policy = AnnotatorPolicy()
            policy.allow_someobjects = False

        ann = t.buildannotator(policy=policy)
        ann.build_types(function, annotations)
        if view or option.view:
            t.view()
        t.buildrtyper(type_system="ootype").specialize()

        if view or option.view:
            t.view()
        #self.js = JS(t, [function, callback_function], stackless)
        self.js = JS(t, function, stackless)
        self.js.write_source()
        if root is None and use_tg:
            from pypy.translator.js.demo.jsdemo.controllers import Root
            self.root = Root
        else:
            self.root = root
        self.run_browser = run_browser
        self.function_calls = []
    
    def source(self):
        return self.js.tmpfile.open().read()

    def _conv(self, v):
        if isinstance(v, str):
            return repr(v)
        return str(v).lower()

    def __call__(self, *kwds):
        return self.call(None, kwds)
    
    def call(self, entry_function, kwds):
        args = ', '.join([self._conv(kw) for kw in kwds]) #lowerstr for (py)False->(js)false, etc.

        if entry_function is None:
            entry_function = self.js.translator.graphs[0].name
        else:
            entry_function = self.js.translator.annotator.bookkeeper.getdesc(entry_function).cached_graph(None)
        function_call = "%s(%s)" % (entry_function, args)
        self.function_calls.append(function_call)
        #if self.js.stackless:
        #    function_call = "slp_entry_point('%s')" % function_call

        if use_browsertest:
            if not use_tg:
                log("Used html: %r" % self.html)
                output = jstest(self.js.filename, function_call, use_browsertest, self.html, self.is_interactive)
            else:
                global port
                from pypy.translator.js.test.tgtest import run_tgtest
                out = run_tgtest(self, tg_root = self.root, port=port, run_browser=self.run_browser).results
                assert out[1] == 'undefined' or out[1] == ""
                output = out[0]
                port += 1
            return self.reinterpret(output)
        else:
#            cmd = 'echo "load(\'%s\'); print(%s)" | js 2>&1' % (self.js.filename, function_call)
#            log(cmd)
#            output = os.popen(cmd).read().strip()
            js = subprocess.Popen(["js"], 
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            input = "load(%r);\n" % self.js.filename.strpath
            for call in self.function_calls[:-1]:
                input += "%s;\n" % call
            input += "print(\"'\" + %s + \"'\");\n" % self.function_calls[-1]
            js.stdin.write(input)
            stdout, stderr = js.communicate()
            output = (stderr + stdout).strip()
        for s in output.split('\n'):
            log(s)

        m = re.match("'(.*)'", output, re.DOTALL)
        if not m:
            log("Error: %s" % output)
            raise JSException(output)
        return self.reinterpret(m.group(1))

    def reinterpret(cls, s):
        #while s.startswith(" "):
        #    s = s[1:] # :-) quite inneficient, but who cares
        if s == 'false':
            res = False
        elif s == 'true':
            res = True
        elif s == 'undefined':
            res = None
        elif s == 'inf':
            res = 1e300 * 1e300
        elif s == 'NaN':
            res = (1e300 * 1e300) / (1e300 * 1e300)
        elif s.startswith('[') or s.startswith('('):
            l = s[1:-1].split(',')
            res = [cls.reinterpret(i) for i in l]
        else:
            try:
                res = float(s)
                if float(int(res)) == res:
                    return int(res)
            except ValueError:
                res = str(s)
        return res
    reinterpret = classmethod(reinterpret)

class JsTest(BaseRtypingTest, OORtypeMixin):
    def _compile(self, _fn, args, policy=None):
        argnames = _fn.func_code.co_varnames[:_fn.func_code.co_argcount]
        func_name = _fn.func_name
        if func_name == '<lambda>':
            func_name = 'func'
        source = py.code.Source("""
        def %s():
            from pypy.rlib.nonconst import NonConstant
            res = _fn(%s)
            if isinstance(res, type(None)):
                return None
            else:
                return str(res)"""
        % (func_name, ",".join(["%s=NonConstant(%r)" % (name, i) for
                                   name, i in zip(argnames, args)])))
        exec source.compile() in locals()
        return compile_function(locals()[func_name], [], policy=policy)

    def string_to_ll(self, s):
        return s
    
    def interpret(self, fn, args, policy=None):
        f = self._compile(fn, args, policy)
        res = f(*args)
        return res

    def interpret_raises(self, exception, fn, args):
        #import exceptions # needed by eval
        #try:
        #import pdb; pdb.set_trace()
        try:
            res = self.interpret(fn, args)
        except JSException, e:
            s = e.args[0]
            assert s.startswith('uncaught exception:')
            assert re.search(exception.__name__, s)
        else:
            raise AssertionError("Did not raise, returned %s" % res)
        #except ExceptionWrapper, ex:
        #    assert issubclass(eval(ex.class_name), exception)
        #else:
        #    assert False, 'function did raise no exception at all'

    def ll_to_string(self, s):
        return str(s)

    def ll_to_list(self, l):
        return l

    def ll_unpack_tuple(self, t, length):
        assert len(t) == length
        return tuple(t)

    def class_name(self, value):
        return value[:-8].split('.')[-1]

    def is_of_instance_type(self, val):
        m = re.match("^<.* object>$", val)
        return bool(m)

    def read_attr(self, obj, name):
        py.test.skip('read_attr not supported on genjs tests')

def check_source_contains(compiled_function, pattern):
    import re
    
    source = compiled_function.js.tmpfile.open().read()
    return re.search(pattern, source)
