import autopath
from pypy.tool import testit

class TestVars(testit.AppTestCase):

    def _test_vars_no_arguments(self):
        self.assertEqual(vars(), locals())

    def _test_vars_too_many_arguments(self):
        self.assertRaises(TypeError, vars,  0, 1)

    def _test_vars_correct_arguments(self):
        class a:
            def __init__(self):
                self.res = 42
        self.assertEqual(vars(a), a.__dict__)
        a1 = a()
        self.assertEqual(vars(a1), a1.__dict__)
        self.assertEqual(vars(a1).get('res'),42)
      
if __name__ == '__main__':
    testit.main()


