
import py

def test_execwith_novars(space): 
    val = space.appexec([], """ 
    (): 
        return 42 
    """) 
    assert space.eq_w(val, space.wrap(42))

def test_execwith_withvars(space): 
    val = space.appexec([space.wrap(7)], """
    (x): 
        y = 6 * x 
        return y 
    """) 
    assert space.eq_w(val, space.wrap(42))

def test_execwith_compile_error(space): 
    excinfo = py.test.raises(SyntaxError, space.appexec, [], """
    (): 
        y y 
    """)
    assert str(excinfo).find('y y') != -1 

    
