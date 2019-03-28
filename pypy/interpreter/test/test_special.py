

class AppTestSpecialTestCase:
    def test_Ellipsis(self):
        assert Ellipsis == Ellipsis
        assert repr(Ellipsis) == 'Ellipsis'
        assert Ellipsis.__class__.__name__ == 'ellipsis'
    
    def test_NotImplemented(self):
        def f():
            return NotImplemented
        assert f() == NotImplemented 
        assert repr(NotImplemented) == 'NotImplemented'
        assert NotImplemented.__class__.__name__ == 'NotImplementedType'
