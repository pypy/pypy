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

    def test_name_argument(self):
        def f(): pass
        item = newtest.TestItem(f, 'g')
        self.assertEqual(item.name, 'g')


class TestTestSuite(unittest.TestCase):
    def check_names(self, test_suite, expected_item_names):
        item_names = [item.name for item in test_suite.items]
        item_names.sort()
        expected_item_names.sort()
        self.assertEqual(item_names, expected_item_names)

    def test_items_from_callables(self):
        def f(): pass
        g = lambda: None
        class X:
            def thisone(self): pass
        ts = newtest.TestSuite()
        ts.add(f, g, X.thisone)
        self.check_names(ts, ['f', '<lambda>', 'thisone'])

    def test_items_from_class(self):
        class X:
            """Docstring - don't find it."""
            def test_this(self): pass
            def no_test(self): pass
            def test_that(self): pass
        ts = newtest.TestSuite()
        ts.add(X)
        self.check_names(ts, ['test_this', 'test_that'])



# used in unit tests above; placed here, so that TestTestItem is accessible
module = inspect.getmodule(TestTestItem)
file = inspect.getsourcefile(TestTestItem)


if __name__ == '__main__':
    unittest.main()
