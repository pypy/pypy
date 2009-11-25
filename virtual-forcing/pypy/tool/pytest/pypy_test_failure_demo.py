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

def app_test_raises_in_statement():
    raises(ValueError, """
        y = x  # name error
    """)

def app_test_raises_something():
    int("hallo") 

def app_test_raises_wrong1():
    raises(SyntaxError, 'int("hello")')

def app_test_raises_wrong2():
    raises(SyntaxError, int, "hello") 

def app_test_raises_doesnt():
    raises(ValueError, int, 3)

def app_test_skip():
    skip("skipped test")
    
    
