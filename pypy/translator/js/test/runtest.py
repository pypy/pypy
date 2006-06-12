'''
    Skipped tests should still be fixed. (or only run with py.test --browser)
    Sests with DONT in front of them will probably not be fixed for the time being.
'''

import py, os
from pypy.translator.translator import TranslationContext
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.js2.js import JS
from pypy.translator.js2.test.browsertest import jstest
from pypy.translator.js2 import conftest
from pypy.translator.js2.log import log
from pypy.conftest import option
log = log.runtest
use_browsertest = conftest.option.browser
use_tg = conftest.option.tg

def _CLI_is_on_path():
    try:
        py.path.local.sysfind('js') #we recommend Spidermonkey
    except py.error.ENOENT:
        return False
    return True

class compile_function(object):
    def __init__(self, function, annotation, stackless=False, view=False, html=None, is_interactive=False):
        if not use_browsertest and not _CLI_is_on_path():
            py.test.skip('Javascript CLI (js) not found')

        self.html = html
        self.is_interactive = is_interactive
        t = TranslationContext()
        t.buildannotator().build_types(function, annotation)

        t.buildrtyper(type_system="ootype").specialize() 
        #print t.rtyper

        #backend_optimizations(t, raisingop2direct_call_all=True, inline_threshold=0, mallocs=False)
        #backend_optimizations(t)
        if view or option.view:
            t.view()
        #self.js = JS(t, [function, callback_function], stackless)
        self.js = JS(t, [function], stackless)
        self.js.write_source()

    def _conv(self, v):
        #if isinstance(v, str):
        #    return "{hash:0, chars:'%s'}" % v
        return str(v).lower()

    def __call__(self, *kwds):
        args = ', '.join([self._conv(kw) for kw in kwds]) #lowerstr for (py)False->(js)false, etc.

        entry_function = self.js.translator.graphs[0].name
        function_call = "%s(%s)" % (entry_function, args)
        #if self.js.stackless:
        #    function_call = "slp_entry_point('%s')" % function_call

        if use_browsertest:
            if not use_tg:
                log("Used html: %r" % self.html)
                output = jstest(self.js.filename, function_call, use_browsertest, self.html, self.is_interactive)
            else:
                from pypy.translator.js2.test.tgtest import run_tgtest
                out = run_tgtest(self, None).results
                assert out[1] == 'undefined'
                output = out[0]
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
            try:
                res = eval(s)
            except:
                res = str(s)
        return res
