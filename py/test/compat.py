from __future__ import generators
from py import test, magic

class TestCaseUnit(test.run.Item):
    """ compatibility Unit executor for TestCase methods
        honouring setUp and tearDown semantics. 
    """
    def execute(self, runner):
        unboundmethod = self.pypath.resolve() 
        cls = unboundmethod.im_class
        instance = cls()
        instance.setUp()
        try:
            unboundmethod(instance) 
        finally:
            instance.tearDown()
        return test.run.Passed()

class TestCase:
    """compatibility class of unittest's TestCase. """
    Item = TestCaseUnit 

    def setUp(self): 
        pass

    def tearDown(self): 
        pass

    def fail(self, msg=None):
        """ fail immediate with given message. """
        raise test.run.Failed(msg=msg) 

    def assertRaises(self, excclass, func, *args, **kwargs):
        test.raises(excclass, func, *args, **kwargs)
    failUnlessRaises = assertRaises

    # dynamically construct (redundant) methods 
    aliasmap = [
        ('x',   'not x', 'assert_, failUnless'),
        ('x',   'x',     'failIf'),
        ('x,y', 'x!=y',  'failUnlessEqual,assertEqual, assertEquals'), 
        ('x,y', 'x==y',  'failIfEqual,assertNotEqual, assertNotEquals'),
        ]
    items = []
    for sig, expr, names in aliasmap:
        names = map(str.strip, names.split(','))
        sigsubst = expr.replace('y', '%s').replace('x', '%s')
        for name in names:
            items.append("""
                def %(name)s(self, %(sig)s):
                    if %(expr)s:
                        raise test.run.Failed(tbindex=-2, msg=%(sigsubst)r %% (%(sig)s))
            """ % locals() )

    source = "".join(items)
    exec magic.dyncode.compile2(source)

__all__ = ['TestCase']
