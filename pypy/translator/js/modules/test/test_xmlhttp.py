
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

def reply_fun(data):
    ProxyRootInstance.send_result(str(data['eight']), "", empty_fun)

def test_proxy_double_side():
    def run_double_proxy():
        ProxyRootInstance.return_eight(reply_fun)
    
    fn = compile_function(run_double_proxy, [], root = ProxyRoot)
    result = fn()
    assert result == 8

