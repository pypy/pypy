
""" Some external functions tests
"""

from pypy.translator.js.test.runtest import compile_function, check_source_contains

def test_set_timeout():
    from pypy.translator.js.modules.dom import setTimeout
    
    def to_timeout():
        pass
    
    def s_timeout_call():
        setTimeout(to_timeout, 300)

    c = compile_function(s_timeout_call, [])
    assert check_source_contains(c, "setTimeout \( 'to_timeout\(\)',300 \)")
