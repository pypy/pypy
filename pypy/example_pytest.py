class AppTestTest: 
    def test_app_method(self):
        assert 42 == 41 

def app_test_app_func(): 
    assert 41 == 42 

def test_interp_func(space): 
    assert space.is_true(space.w_None) 

class TestInterpTest: 
    def test_interp_method(self): 
        assert self.space.is_true(self.space.w_False) 

