import sys
from py import test
from py.__impl__.test.tool.outerrcapture import SimpleOutErrCapture 

def test_capturing_simple():
    cap = SimpleOutErrCapture()
    print "hello world"
    print >>sys.stderr, "hello error"
    out, err = cap.reset()
    assert out == "hello world\n"
    assert err == "hello error\n"

def test_capturing_error():
    cap = SimpleOutErrCapture()
    print "hello"
    cap.reset()
    test.raises(AttributeError, "cap.reset()")

def test_capturing_error_recursive():
    cap = SimpleOutErrCapture()
    cap2 = SimpleOutErrCapture()
    print "hello"
    cap2.reset()
    test.raises(AttributeError, "cap2.reset()")

test.main()
