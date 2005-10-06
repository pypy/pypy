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

def write_wrapper(js_filename):
    jswrapper_filename = js_filename.new(ext='_wrapper.js')
    f = open(str(jswrapper_filename), 'w')
    f.write('print(42);\n')
    f.close()
    log('Written:', jswrapper_filename)
    return jswrapper_filename

class jscallable(object):
    def __init__(self, jswrapper_filename):
        self.jswrapper_filename = jswrapper_filename
        
    def __call__(self):
        cmd = 'js "%s"' % str(self.jswrapper_filename)
        s   = os.popen(cmd).read()
        e   = eval(s)
        return e
    
def compile(function, annotation=[], view=False):
    if not _CLI_is_on_path():
        py.test.skip('Javascript CLI (js) not found')

    t = Translator(function)
    a = t.annotate(annotation)
    a.simplify()
    t.specialize()
    t.backend_optimizations()
    if view:
        t.view()

    js = JS(t, function)
    log('Written:', js.filename)

    jswrapper_filename = write_wrapper(js.filename)
    return jscallable(jswrapper_filename)
