

class AppTestDescrTypecheck:

    def test_getsetprop_get(self):
        def f():
            pass
        raises(TypeError, type(f).__dict__['func_code'].__get__.im_func,1,None)

    def test_func_code_get(self):
        def f():
            pass
        raises(TypeError, type(f).func_code.__get__,1)
