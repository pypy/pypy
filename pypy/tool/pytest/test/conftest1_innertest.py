
def test_something(space): 
    assert space.w_None is space.w_None 

def app_test_something(): 
    assert 42 == 42 

def app_test_code_in_docstring_failing():
    """
    assert False
    """

class AppTestSomething: 
    def test_method_app(self): 
        assert 23 == 23

    def test_code_in_docstring_failing(self):
        """
        assert False # failing test
        """

    def test_code_in_docstring_ignored(self):
        """
        this docstring is not parsed as code because the function body is not
        empty
        """
        assert True

    
class TestSomething:
    def test_method(self): 
        assert self.space 
 
def app_test_raise_in_a_closure():
    def f(x):
        raises(AttributeError, "x.foo")
    f(42)
