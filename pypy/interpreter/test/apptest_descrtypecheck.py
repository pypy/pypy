import pytest

def test_getsetprop_get():
    def f():
        pass
    getter =  type(f).__dict__['func_code'].__get__
    getter = getattr(getter, 'im_func', getter) # neutralizes pypy/cpython diff
    with pytest.raises(TypeError):
        getter(1, None)

def test_func_code_get():
    def f():
        pass
    with pytest.raises(TypeError):
        type(f).func_code.__get__(1)
