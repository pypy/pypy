import autopath
import imp
import os
import sys
import unittest
import vpath


# named constants for test result status values
SUCCESS = 'success'
ERROR = 'error'
FAILURE = 'failure'
IGNORED = 'ignored'
SKIPPED = 'skipped'

class TestResult:
    """Represent the result of a run of a test item."""
    def __init__(self, item, status=None, fullname=None, traceback=None):
        # one of SUCCESS, ERROR, FAILURE, IGNORED, SKIPPED
        self.status = None
        # name of the test method (without class or module name)
        self.methodname = None
        # full method name (with module path and class name)
        self.fullname = None
        # traceback object if applicable, else None
        self.traceback = None
        # formatted traceback (a string)
        self.formatted_traceback = None


class TestItem:
    """Represent a single test method from a TestCase class."""
    def __init__(self, testmethod):
        #TODO implement the code to initialze these attributes
        self.module = None
        self.file = None
        self.lineno = None
        self.source = None
        self._method = testmethod
        self._class = testmethod.__class__

    def run(self):
        """Run this TestItem and return a corresponding TestResult object."""
        #XXX at a later time, this method may accept an object space
        #  as argument

    def __str__(self):
        return "TestItem from method %s" % self._method

    __repr__ = __str__


class TestSuite:
    """Represent a collection of test items."""
    def __init__(self):
        self.items = []

    def _items_from_module(self, module):
        """Return a list of TestItems read from the given module."""
        items = []
        # scan the module for classes derived from unittest.TestCase
        for obj in vars(module).values():
            try:
                is_testclass = issubclass(obj, unittest.TestCase)
            except TypeError:
                # not a class at all; ignore it
                continue
            if not is_testclass:
                continue
            # scan class for test methods
            for obj in vars(obj).values():
                if hasattr(obj, 'func_code') and \
                  obj.__name__.startswith("test"):
                    items.append(TestItem(obj))
        return items

    def _module_from_modpath(self, modpath):
        """
        Return a module object derived from the module path
        (e. g. "pypy.module.builtin.test.test_minmax").
        """
        # This __import__ call is only used to ensure that the module
        # is present in sys.modules. Unfortunately, the module returned
        # from the __import__ function doesn't correspond to the last
        # component of the module path but the first. In the example
        # listed in the docstring we thus would get the pypy module,
        # not the test_minmax module.
        __import__(modpath)
        return sys.modules[modpath]

    def initfromdir(self, dirname, filterfunc=None, recursive=True,
                    loader=None):
        """
        Init this suite by reading the directory denoted by dirname,
        then find all test modules in it. Test modules are files that
        comply with the shell pattern shell_pattern "test_*.py".

        filterfunc is a callable that can be used to filter the test
        modules by module path. By default, all test modules are used.

        If recursive is true, which is the default, find all test modules
        by scanning the start directory recursively. The argument loader
        may be set to a test loader class to use. By default, the
        TestLoader class from the unittest module is used.
        """
        dirname = vpath.getlocal(dirname)
        if loader is None:
            loader = unittest.TestLoader()

        def testfilefilter(path):
            return path.isfile() and path.fnmatch('test_*.py')
        def recfilter(path):
            return recursive and vpath.nodotfile(path)

        for testfn in dirname.visit(testfilefilter, recfilter):
            # strip the leading pypy directory and the .py suffix
            modpath = str(testfn)[len(autopath.pypydir)+1:-3]
            modpath = 'pypy.' + modpath.replace(os.sep, '.')
            if (filterfunc is None) or filterfunc(modpath):
                try:
                    module = self._module_from_modpath(modpath)
                    items = self._items_from_module(module)
                except:
                    print "skipping testfile (failed loading it)", modpath
                else:
                    self.items.extend(items)


if __name__ == '__main__':
    ts = TestSuite()
    ts.initfromdir(".")
    print ts.items

