import inspect
import unittest

import autopath
from pypy.tool import newtest


class TestTestItem(unittest.TestCase):
    def _test_function(self, func, expected_name):
        item = newtest.TestItem(func)
        self.assertEqual(item.name, expected_name)
        self.assertEqual(item.call_via_class, False)
        self.assertEqual(item.cls, None)
        self.failUnless(item.module is module)
        self.assertEqual(item.file, file)

    def test_plain_function(self):
        f = lambda: 'anything'
        self._test_function(f, expected_name='<lambda>')
        def f(): pass
        self._test_function(f, expected_name='f')

    def test_bound_method(self):
        class X:
            def f(self): pass
        x = X()
        item = newtest.TestItem(x.f)
        self.assertEqual(item.name, 'f')
        self.assertEqual(item.call_via_class, False)
        self.failUnless(item.cls is X)
        self.failUnless(item.module is module)
        self.assertEqual(item.file, file)

    def test_unbound_method(self):
        class X:
            def f(self): pass
        item = newtest.TestItem(X.f)
        self.assertEqual(item.name, 'f')
        self.assertEqual(item.call_via_class, True)
        self.failUnless(item.cls is X)
        self.failUnless(item.module is module)
        self.assertEqual(item.file, file)

    def test_class_instance(self):
        class X:
            def __call__(self): pass
        item = newtest.TestItem(X())
        self.assertEqual(item.name, '<unnamed object>')
        self.assertEqual(item.call_via_class, False)
        self.failUnless(item.cls is X)
        self.failUnless(item.module is module)
        self.assertEqual(item.file, file)

    #XXX best way to trigger execptions in TestItem's constructor
    # without getting rather complicated?

    def test_docstrings(self):
        class X:
            def f(self):
                "Method docstring"
        item = newtest.TestItem(X.f)
        self.assertEqual(item.docs, ('', '', "Method docstring"))

        class X:
            "Class docstring"
            def f(self): pass
        item = newtest.TestItem(X.f)
        self.assertEqual(item.docs, ('', "Class docstring", ''))

    def test_items_from_class(self):
        ts = newtest.TestSuite()
        ts._items_from_class(TestTestItem)


# used in unit tests above; placed here, so that TestTestItem is accessible
module = inspect.getmodule(TestTestItem)
file = inspect.getsourcefile(TestTestItem)


if __name__ == '__main__':
    unittest.main()
