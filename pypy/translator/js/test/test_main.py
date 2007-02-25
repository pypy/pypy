
""" tests of rpython2javascript function
"""

from pypy.translator.js.main import rpython2javascript, rpython2javascript_main,\
     js_optiondescr
from pypy.translator.js import conftest
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, described
import py
import sys
from pypy.tool.udir import udir
from pypy.config.config import Config, to_optparse


#if not conftest.option.browser:
#    py.test.skip("Works only in browser (right now?)")

def setup_module(mod):
    mod.jsconfig = Config(js_optiondescr)

class A(BasicExternal):
    def method(self, a={'a':'a'}):
        pass
    method = described(retval={str:str})(method)

a = A()
a._render_name = 'a'

def fun(x='3'):
    return a.method({'a':x})['a']

def fff():
    pass

def test_bookkeeper_cleanup():
    assert rpython2javascript(sys.modules[__name__], ["fun"])
    assert rpython2javascript(sys.modules[__name__], ["fun"])

def test_module_none():
    assert rpython2javascript(None, "fff")

class TestJsMain(object):
    def _test_not_raises(self, mod_file, args_rest=[]):
        try:
            rpython2javascript_main([str(mod_file)] + args_rest,
                                           jsconfig)
        except SystemExit:
            py.test.fail("Exited")

    def _test_raises(self, mod_file, args_rest):
        py.test.raises(SystemExit, rpython2javascript_main,
            [str(mod_file)] + args_rest, jsconfig)

    def test_main_one(self):
        udir.ensure("js_one.py").write(py.code.Source("""
        def f():
            pass
        f._client = True
        """))
        self._test_not_raises(udir.join("js_one.py"))

    def test_main_two(self):
        udir.ensure("js_two.py").write(py.code.Source("""
        def f():
            pass
        """))
        self._test_not_raises(udir.join("js_two.py"), ["f"])
        self._test_raises(udir.join("js_two.py"), [])

