class TestCase:
    """compatibility class of unittest's TestCase. """
    def setUp(self):
        pass

    def tearDown(self):
        pass
    
    def assertEqual(self, x, y, msg=None): 
        if msg: 
            assert x == y, msg 
        else: 
            assert x == y 
    def assertNotEqual(self, x, y, msg=None): 
        if msg: 
            assert x != y, msg 
        else: 
            assert x != y 

    def assertRaises(self, exc, call, *args, **kwargs): 
        raises(exc, call, *args, **kwargs) 

    assertEquals = assertEqual 
    assertNotEquals = assertNotEqual 
    def assert_(self, expr, msg=None): 
        if msg: 
            assert expr, msg 
        else: 
            assert expr 
