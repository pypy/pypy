
import py

from pypy.lib._formatting import format, NeedUnicodeFormattingError

def test_charformatter():
    res = format("%c", ("a",))
    assert res == "a"
    res = format("%c", (ord("b"),))
    assert res == "b"
    py.test.raises(TypeError, 
        "format('%c', ('qw',))")
    #py.test.raises(NeedUnicodeFormattingError, 
    #    "format(u'%c', (u'b',))")
    
