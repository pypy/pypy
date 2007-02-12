
""" Tests for support module
"""

from pypy.translator.js.lib import support

def test_callback():
    @support.callback(retval=int)
    def f(self, a=8, b=3.2):
        pass

    methdesc = f._method[1]
    assert len(methdesc.args) == 3
    assert methdesc.args[2].name == 'callback'

