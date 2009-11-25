

def app_test_raises():
    info = raises(TypeError, id)
    assert info.type is TypeError
    assert isinstance(info.value, TypeError)

    x = 43
    info = raises(ZeroDivisionError, "x/0")
    assert info.type is ZeroDivisionError    
    assert isinstance(info.value, ZeroDivisionError)    
