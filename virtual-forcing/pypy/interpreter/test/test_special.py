

class AppTestSpecialTestCase:
    def test_Ellipsis(self):
        assert Ellipsis == Ellipsis
        assert repr(Ellipsis) == 'Ellipsis'
    
    def test_NotImplemented(self):
        def f():
            return NotImplemented
        assert f() == NotImplemented 
        assert repr(NotImplemented) == 'NotImplemented'
