import py

def setup_module(mod):
    py.magic.invoke(assertion=1) 

def teardown_module(mod):
    py.magic.revoke(assertion=1) 

def f():
    return 2

def test_assert():
    try:
        assert f() == 3
    except AssertionError, e:
        s = str(e)
        assert s.startswith('assert 2 == 3\n')

def test_assert_within_finally(): 
    class A: 
        def f():
            pass 
    excinfo = py.test.raises(TypeError, """
        try:
            A().f()
        finally:
            i = 42
    """)
    s = str(excinfo[1])
    assert s.find("takes no argument") != -1

    #def g():
    #    A.f()
    #excinfo = getexcinfo(TypeError, g)
    #msg = getmsg(excinfo)
    #assert msg.find("must be called with A") != -1


def test_assert_multiline_1():
    try:
        assert (f() ==
                3)
    except AssertionError, e:
        s = str(e)
        assert s.startswith('assert 2 == 3\n')

def test_assert_multiline_2():
    try:
        assert (f() == (4,
                   3)[-1])
    except AssertionError, e:
        s = str(e)
        assert s.startswith('assert 2 ==')
