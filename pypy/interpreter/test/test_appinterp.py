
import py

def test_execwith_novars(space): 
    val = space.exec_with("""
        return 42
    """) 
    assert space.eq_w(val, space.wrap(42))

def test_execwith_withvars(space): 
    val = space.exec_with("""
        y = 6 * x 
        return y 
    """, x = space.wrap(7)) 
    assert space.eq_w(val, space.wrap(42))


def test_execwith_compile_error(space): 
    excinfo = py.test.raises(SyntaxError, space.exec_with, """
        y y 
    """)
    assert str(excinfo).find('y y') != -1 

    
