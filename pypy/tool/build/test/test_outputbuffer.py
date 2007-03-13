import sys
from StringIO import StringIO
from pypy.tool.build.outputbuffer import OutputBuffer

def test_output_buffer():
    b = OutputBuffer()
    sys.stdout = b
    try:
        print 'foo'
    finally:
        sys.stdout = sys.__stdout__
    assert b.getvalue() == 'foo\n'

    s = StringIO()
    b = OutputBuffer(s)
    sys.stdout = b
    try:
        print 'bar'
    finally:
        sys.stdout = sys.__stdout__
    assert b.getvalue() == s.getvalue() == 'bar\n'

