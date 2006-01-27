import py, os
from pypy.translator.translator import TranslationContext
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.js.js import JS
from pypy.translator.js.test.browsertest import jstest
from pypy.translator.js import conftest
from pypy.translator.js.log import log
log = log.runtest
use_browsertest = conftest.option.jsbrowser

def _CLI_is_on_path():
    try:
        py.path.local.sysfind('js') #we recommend Spidermonkey
    except py.error.ENOENT:
        return False
    return True

class compile_function(object):
    def __init__(self, function, annotation, stackless=False, view=False):
        if not use_browsertest and not _CLI_is_on_path():
            py.test.skip('Javascript CLI (js) not found')

        t = TranslationContext()
        t.buildannotator().build_types(function, annotation)

        t.buildrtyper().specialize() 

        backend_optimizations(t, raisingop2direct_call_all=True, inline_threshold=0, mallocs=False)
        #backend_optimizations(t)
        if view:
            t.view()
        #self.js = JS(t, [function, callback_function], stackless)
        self.js = JS(t, [function], stackless)
        self.js.write_source()

    def _conv(self, v):
        if isinstance(v, str):
            return "{hash:0, chars:'%s'}" % v
        return str(v).lower()

    def __call__(self, *kwds):
        args = ', '.join([self._conv(kw) for kw in kwds]) #lowerstr for (py)False->(js)false, etc.

        entry_function = self.js.graph[0].name
        function_call = "%s(%s)" % (entry_function, args)
        if self.js.stackless:
            function_call = "slp_entry_point('%s')" % function_call

        if use_browsertest:
            output = jstest(self.js.filename, function_call)
        else:
            cmd = 'echo "load(\'%s\'); print(%s)" | js 2>&1' % (self.js.filename, function_call)
            log(cmd)
            output = os.popen(cmd).read().strip()
        for s in output.split('\n'):
            log(s)

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
        else:
            log('javascript result:', s)
            res = eval(s)
        return res
