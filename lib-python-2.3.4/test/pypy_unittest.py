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

    def failIfEqual(self, x, y, msg=None): 
        if msg: 
            assert not x == y, msg 
        else: 
            assert not x == y 

    def failUnless(self, expr, msg=None):
        if msg is None:
            assert expr
        else:
            assert expr, msg

    def failIf(self, expr, msg=None):
        if msg is None:
            assert not expr
        else:
            assert not expr, msg

    def fail(self, msg):
        assert False, msg
        
    def assertRaises(self, exc, call, *args, **kwargs): 
        raises(exc, call, *args, **kwargs) 

    def assertAlmostEqual(self, x, y, places=7, msg=None):
        if msg is None:
            msg = '%r != %r within %r places' %(x, y, places)
        assert round(y-x, places) == 0, msg

    def assertNotAlmostEqual(self, x, y, places=7, msg=None):
        if msg is None:
            msg = '%r == %r within %r places' %(x, y, places)
        assert round(y-x, places) != 0, msg

    assertEquals = assertEqual 
    assertNotEquals = assertNotEqual 
    failUnlessRaises = assertRaises
    failUnlessEqual = assertEqual
    failIfAlmostEqual = assertNotAlmostEqual
    failUnlessAlmostEqual = assertAlmostEqual
    
    def assert_(self, expr, msg=None): 
        if msg: 
            assert expr, msg 
        else: 
            assert expr 
