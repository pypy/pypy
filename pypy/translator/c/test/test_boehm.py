import py
test_src = """
from pypy.translator.translator import Translator
from pypy.translator.tool.cbuild import skip_missing_compiler
from pypy.translator.c.genc import CExtModuleBuilder

def getcompiled(func):
    from pypy.translator.c.gc import BoehmGcPolicy
    t = Translator(func, simplifying=True)
    # builds starting-types from func_defs 
    argstypelist = []
    if func.func_defaults:
        for spec in func.func_defaults:
            if isinstance(spec, tuple):
                spec = spec[0] # use the first type only for the tests
            argstypelist.append(spec)
    a = t.annotate(argstypelist)
    a.simplify()
    t.specialize()
    t.checkgraphs()
    def compile():
        cbuilder = CExtModuleBuilder(t, gcpolicy=BoehmGcPolicy)
        c_source_filename = cbuilder.generate_source()
        cbuilder.compile()
        cbuilder.import_module()    
        return cbuilder.get_entry_point()
    return skip_missing_compiler(compile)


def test_malloc_a_lot():
    def malloc_a_lot():
        i = 0
        while i < 10:
            i += 1
            a = [1] * 10
            j = 0
            while j < 20:
                j += 1
                a.append(j)
    fn = getcompiled(malloc_a_lot)
    fn()

def run_test(fn):
    fn()
    channel.send(None)

run_test(test_malloc_a_lot)
"""


def test_boehm():
    import py
    py.test.skip("boehm test is fragile wrt. the number of dynamically loaded libs")
    from  pypy.translator.tool import cbuild
    if not cbuild.check_boehm_presence():
        py.test.skip("no boehm gc on this machine")
    gw = py.execnet.PopenGateway()
    chan = gw.remote_exec(py.code.Source(test_src))
    res = chan.receive()
    assert not res
    chan.close()


