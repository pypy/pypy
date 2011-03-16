
def test_something(space): 
    assert space.w_None is space.w_None 

def app_test_something(): 
    assert 42 == 42 

class AppTestSomething: 
    def test_method_app(self): 
        assert 23 == 23 
    
class TestSomething:
    def test_method(self): 
        assert self.space 
 
