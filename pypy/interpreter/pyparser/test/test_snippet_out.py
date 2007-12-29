import os, sys, re
import dis, StringIO
from pypy.interpreter.pyparser.test import test_astbuilder
from pypy.interpreter.pyparser.test import test_astcompiler

SNIPPETS = test_astbuilder.SNIPPETS

# ____________________________________________________________

def generate_output(snippet_name, space):
    filepath = os.path.join(os.path.dirname(__file__),
                            'samples', snippet_name)
    source = file(filepath).read()
    ac_code = test_astcompiler.compile_with_astcompiler(source,
                                                        mode='exec',
                                                        space=space)
    text = dump_code(ac_code, space)
    return '%s\n%s\n%s' % (source,
                           '=' * 79,
                           text)

def get_output_path(snippet_name):
    outputpath = os.path.join(os.path.dirname(__file__),
                              'output', snippet_name)
    assert outputpath.endswith('.py')
    outputpath = outputpath[:-3] + '.txt'
    return outputpath

# ____________________________________________________________

r_addr = re.compile(r" object at -?0x[0-9a-fA-F]+")

def dump_code(co, space=None):
    if not hasattr(co, 'co_consts'):
        co = test_astcompiler.to_code(co, space)
    saved = sys.stdout
    try:
        sys.stdout = f = StringIO.StringIO()
        print 'co_filename = %r' % (co.co_filename,)
        print 'co_varnames = %r' % (co.co_varnames,)
        print 'co_flags    = %r' % (co.co_flags,)
        dis.dis(co)
        print 'co_consts:'
        for i, x in enumerate(co.co_consts):
            if hasattr(x, 'co_code'):
                sub = dump_code(x, space)
                x = sub.replace('\n', '\n    ').rstrip()
            else:
                x = repr(x)
            print '[%d]' % i, x
    finally:
        sys.stdout = saved
    text = f.getvalue()
    text = r_addr.sub(" object at xxx", text)
    return text

# ____________________________________________________________

def setup_module(mod):
    import pypy.conftest
    mod.std_space = pypy.conftest.gettestobjspace('std')

for snippet_name in SNIPPETS:
    def _test_snippet(snippet_name=snippet_name):
        result = generate_output(snippet_name, std_space)
        print result + '===RESULT=END==='
        f = open(get_output_path(snippet_name), 'r')
        expected = f.read()
        f.close()
        if result != expected:
            print expected + '===EXPECTED=END==='
            assert False, "expected a different result!"

    globals()['test_' + snippet_name] = _test_snippet
