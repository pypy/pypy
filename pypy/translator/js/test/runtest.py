import py, os
from pypy.translator.translator import Translator
from pypy.translator.js.js import JS
from pypy.translator.js.log import log
log = log.runtest


def _CLI_is_on_path():
    try:
        py.path.local.sysfind('js') #we recommend Spidermonkey
    except py.error.ENOENT:
        return False
    return True

class compile_function(object):
    def __init__(self, function, annotation, view=False):
        if not _CLI_is_on_path():
            py.test.skip('Javascript CLI (js) not found')

        t = Translator(function)
        a = t.annotate(annotation)
        a.simplify()
        t.specialize()
        t.backend_optimizations()
        if view:
            t.view()
        self.js = JS(t, function)
        self.js.write_source()

    def __call__(self, *kwds):
        #note: lowercase string for (py)False->(js)false, etc.
        args = ' '.join([str(kw).lower() for kw in kwds])
        cmd = 'js %s %s' % (self.js.filename, args)
        log(cmd)
        s   = os.popen(cmd).read()
        res = eval(s)
        return res
