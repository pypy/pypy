import py, os
from pypy.translator.translator import Translator
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

        t = Translator(function)
        a = t.annotate(annotation)
        t.specialize()
        t.backend_optimizations(inline_threshold=0, mallocs=False)
        #t.backend_optimizations()
        if view:
            t.view()
        self.js = JS(t, function, stackless)
        self.js.write_source()

    def __call__(self, *kwds):
        args = ', '.join([str(kw).lower() for kw in kwds]) #lowerstr for (py)False->(js)false, etc.

        if use_browsertest:
            jstestcase = '%s(%s)' % (self.js.graph.name, args)
            output = jstest(self.js.filename, jstestcase)
        else:
            wrappercode = self.js.wrappertemplate % args
            cmd = 'echo "%s" | js 2>&1' % wrappercode
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
