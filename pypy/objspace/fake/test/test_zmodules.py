from pypy.config.pypyoption import working_modules
from pypy.objspace.fake.checkmodule import checkmodule
from pypy.tool.sourcetools import compile2


for name in sorted(working_modules):
    exec compile2("""\
        def test_module_%s():
            checkmodule(%r)
    """ % (name, name))
