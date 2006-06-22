
""" xmlhttp proxy test
"""

from pypy.translator.js.demo.jsdemo.proxy import ProxyRootInstance, ProxyRoot
from pypy.translator.js.test.runtest import compile_function

def empty_fun(d):
    pass

def test_basic_proxy():
    def run_proxy():
        ProxyRootInstance.send_result("3", "", empty_fun)
    
    fn = compile_function(run_proxy, [], root = ProxyRoot)
    result = fn()
    assert result == 3

#def test_proxy_double_side
