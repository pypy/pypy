"""
Unit testing framework for PyPy.

The following picture is an UML class diagram of the framework.

+------------+ 1                                    1 +----------+
| TestResult |----------------------------------------| TestItem |
| (abstract) |                                        +----------+
+------------+                                             | *
    A                                                      |
    -                                                      |
    |                                                      | 1
    +----------------------------+-----------+        +-----------+
    |                            |           |        | TestSuite |
+-------------------------+ +---------+ +---------+   +-----------+
| TestResultWithTraceback | | Success | | Skipped |         A
| (abstract)              | +---------+ +---------+         |
+-------------------------+                                 | loaded by
    A          A                                            |
    -          -                                            | *
    |          |                                      +------------+
    |          |                                      | TestCase   |
+-------+ +---------+                                 | (abstract) |
| Error | | Failure |                                 +------------+
+-------+ +---------+                                       A
                                                            -
                                                            |
                                                            |
                                                       concrete test
                                                       case classes

Like the unittest framework of Python, our framework implements
tests as test methods in TestCase classes. Custom test case classes
derive from the shown TestCase class, defined in this module. As in
Python's unittest, a test case class can contain setUp and tearDown
methods. Additionally, it contains a method 'skip' which can be
called to stop a test prematurely. This won't be counted as a failure
or error.

Test cases are loaded by a TestSuite class via the method init_from_dir.
This method will read all test modules in and below a specified
directory, inspect them for classes derived from TestCase (i. e. _our_
TestCase), and in turn inspect them for test methods (like in
unittest, all methods which start with "test").

For every found method, TestSuite will store its module, class and
unbound method objects in a TestItem object. There are also other
properties stored, e. g. the source code for each method and its
docstring.

When the TestSuite's method 'run' is called, all collected TestItems
are run and, according to the outcome of the test, a TestResult object
is generated which holds a reference to "its" TestItem object.

The TestResult classes Success and Skipped denote a passed test. A
skipped test means that not all test code has been run (and no error
or failure occurred before the skip method was called). If a test
fails, resulting in a Failure object, a test, e. g. tested with
assertEqual, has failed. An Error object is generated if something
else causes an unforeseen exception to be raised.
"""

# for Python 2.2 compatibilty
from __future__ import generators

import autopath
import inspect
import os
import sys
import cStringIO as StringIO
import traceback
import vpath

#TODO
# - add support for ignored tests (do we need to differentiate between
#   skipped and ignored tests at all?)
# - support TestItem.run with different object spaces
# - unify naming of methods/functions; what about the TestCase class?
# - support for pickling and retrieving TestItems and TestResults?

#
# custom TestCase class (adapted from Python's unittest module)
#
class TestCase:
    """A class whose instances are single test cases.

    By default, the test code itself should be placed in a method named
    'runTest'.

    If the fixture may be used for many test cases, create as
    many test methods as are needed. When instantiating such a TestCase
    subclass, specify in the constructor arguments the name of the test method
    that the instance is to execute.

    Test authors should subclass TestCase for their own tests. Construction
    and deconstruction of the test's environment ('fixture') can be
    implemented by overriding the 'setUp' and 'tearDown' methods respectively.
    """
    def setUp(self):
        "Hook method for setting up the test fixture before exercising it."
        pass

    def tearDown(self):
        "Hook method for deconstructing the test fixture after testing it."
        pass

    def skip(self, msg=None):
        """Skip this test by raising exception Skipped."""
        raise Skipped(msg=msg)

    def fail(self, msg=None):
        """Fail immediately, with the given message."""
        raise Failure(msg=msg)

    def failIf(self, expr, msg=None):
        """Fail the test if the expression is true."""
        if expr:
            raise Failure(msg=msg)

    def failUnless(self, expr, msg=None):
        """Fail the test unless the expression is true."""
        if not expr:
            raise Failure(msg=msg)

    def failUnlessRaises(self, excClass, callableObj, *args, **kwargs):
        """
        Fail unless an exception of class excClass is thrown
        by callableObj when invoked with arguments args and keyword
        arguments kwargs. If a different type of exception is
        thrown, it will not be caught, and the test case will be
        deemed to have suffered an error, exactly as for an
        unexpected exception.
        """
        try:
            callableObj(*args, **kwargs)
        except excClass:
            return
        else:
            if hasattr(excClass,'__name__'):
                excName = excClass.__name__
            else:
                excName = str(excClass)
            raise Failure(msg=excName)

    def failUnlessEqual(self, first, second, msg=None):
        """
        Fail if the two objects are unequal as determined by the '=='
        operator.
        """
        if not first == second:
            raise Failure(msg=(msg or '%s != %s' % (`first`, `second`)))

    def failIfEqual(self, first, second, msg=None):
        """
        Fail if the two objects are equal as determined by the '=='
        operator.
        """
        if first == second:
            raise Failure(msg=(msg or '%s == %s' % (`first`, `second`)))

    def failUnlessAlmostEqual(self, first, second, places=7, msg=None):
        """
        Fail if the two objects are unequal as determined by their
        difference rounded to the given number of decimal places
        (default 7) and comparing to zero.

        Note that decimal places (from zero) is usually not the same
        as significant digits (measured from the most signficant digit).
        """
        if round(second-first, places) != 0:
            raise Failure(msg=(msg or '%s != %s within %s places' %
                                      (`first`, `second`, `places`)))

    def failIfAlmostEqual(self, first, second, places=7, msg=None):
        """
        Fail if the two objects are equal as determined by their
        difference rounded to the given number of decimal places
        (default 7) and comparing to zero.

        Note that decimal places (from zero) is usually not the same
        as significant digits (measured from the most signficant digit).
        """
        if round(second-first, places) == 0:
            raise Failure(msg=(msg or '%s == %s within %s places' %
                                      (`first`, `second`, `places`)))

    # aliases
    assertEqual = assertEquals = failUnlessEqual
    assertNotEqual = assertNotEquals = failIfEqual
    assertAlmostEqual = assertAlmostEquals = failUnlessAlmostEqual
    assertNotAlmostEqual = assertNotAlmostEquals = failIfAlmostEqual
    assertRaises = failUnlessRaises
    assert_ = failUnless


# provide services from TestCase class also to test functions, e. g.
# def test_func4711():
#     service.assertEqual(3, 3.0, msg="objects with same value should be equal")
#XXX maybe use another name instead of 'service'
service = TestCase()

#
# TestResult class family
#
class TestResult(Exception):
    """Abstract class representing the outcome of a test."""
    def __init__(self, msg="", item=None):
        Exception.__init__(self, msg)
        self.msg = msg
        self.item = item
        self.name = self.__class__.__name__
        self.traceback = None

    #XXX possibly, we need an attribute/method has_traceback?

    def __eq__(self, other):
        """
        Return True if both TestResult objects are semantically the same.
        Else, return False.
        """
        # trivial case
        if (self is other) or (self.item is other.item):
            return True
        return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return id(self.item)

class Success(TestResult):
    pass

class Skipped(TestResult):
    pass

class Ignored(TestResult):
    pass


class TestResultWithTraceback(TestResult):
    def __init__(self, msg='', item=None):
        TestResult.__init__(self, msg, item)
        self.set_exception()

    def __eq__(self, other):
        return TestResult.__eq__(self, other) and \
               self.formatted_traceback == other.formatted_traceback

    def set_exception(self):
        self.excinfo = sys.exc_info()
        self.traceback = self.excinfo[2]
        # store formatted traceback
        output = StringIO.StringIO()
        args = self.excinfo + (None, output)
        traceback.print_exception(*args)
        # strip trailing newline
        self.formatted_traceback = output.getvalue().rstrip()

class Error(TestResultWithTraceback):
    pass

class Failure(TestResultWithTraceback):
    pass

#
# other classes
#
class TestItem:
    """
    Represent either a test function, or a single test method from a
    TestCase class.
    """
    def __init__(self, module, callable=None, cls=None):
        """
        Construct a test item. The argument callable must be either a
        plain function or an unbound method of a class. In the latter
        case, the argument cls must receive the test case class.
        """
        # do we have a plain function, or a class and a method?
        self.isfunction = (cls is None)
        self.file = inspect.getsourcefile(module)
        self.module = module
        self.callable = callable
        self.cls = cls
        # remove trailing whitespace but leave things such indentation
        # of first line(s) alone
        self.docs = (self._docstring(module), self._docstring(cls),
                     self._docstring(callable))
        #XXX inspect.getsourcelines may fail if the file path stored
        #  in a module's pyc/pyo file doesn't match the py file's
        #  actual location. This can happen if a py file, together with
        #  its pyc/pyo file is moved to a new location. See Python
        #  bug "[570300] inspect.getmodule symlink-related failure":
        #  http://sourceforge.net/tracker/index.php?func=detail&aid=570300&group_id=5470&atid=105470
        lines, self.lineno = inspect.getsourcelines(callable)
        # removing trailing newline(s) but not the indentation
        self.source = ''.join(lines).rstrip()

    def _docstring(self, obj):
        """
        Return the docstring of object obj or an empty string, if the
        docstring doesn't exist, i. e. is None.
        """
        if obj is None:
            return None
        return inspect.getdoc(obj) or ""

    def __eq__(self, other):
        """
        Return True if this and the other item compare equal. (This doesn't
        necessarily mean that they are the same object.) Else, return False.
        """
        # trivial case
        if self is other:
            return True
        # If module, cls and unbound method are the same, the files must
        # also be equal. For the methods, we compare the names, not the
        # methods themselves; see
        # http://mail.python.org/pipermail/python-list/2002-September/121655.html
        # for an explanation.
        if (self.module is other.module) and (self.cls is other.cls) and \
          (self.callable.__name__ == other.callable.__name__):
            return True
        return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return id(self.module) ^ id(self.cls)

    # credit: adapted from Python's unittest.TestCase.run
    def run(self, test_runner=lambda callable: callable()):
        """
        Run this TestItem and return a corresponding TestResult object.

        If the test item corresponds to a class method, the setUp and
        tearDown methods of the associated class are called before and
        after the invocation of the test method, repectively.

        If the optional argument test_runner is absent, the test function
        or method is merely called with no arguments. Else, test_runner
        must be a callable accepting one argument. Instead of only calling
        the test callable, the test_runner object will be called with the
        test function/method as its argument.
        """
        if self.isfunction:
            # use the test function directly
            test = self.callable
        else:
            # turn the test callable, an unbound method, into a bound method
            cls_object = self.cls()
            test = getattr(cls_object, self.callable.__name__)

        try:
            # call setUp only for a class
            self.isfunction or cls_object.setUp()
        except KeyboardInterrupt:
            raise
        except TestResult, result:
            # reconstruct TestResult object, implicitly set exception
            return result.__class__(msg=result.msg, item=self)
        except Exception, exc:
            return Error(msg=str(exc), item=self)

        try:
            test_runner(test)
            result = Success(msg='success', item=self)
        except KeyboardInterrupt:
            raise
        except TestResult, result:
            # reconstruct TestResult object, implicitly set exception
            result = result.__class__(msg=result.msg, item=self)
        except Exception, exc:
            result = Error(msg=str(exc), item=self)

        try:
            # call tearDown only for a class
            self.isfunction or cls_object.tearDown()
        except KeyboardInterrupt:
            raise
        except Exception, exc:
            # if we already had an exception in the test method,
            # don't overwrite it
            if result.traceback is None:
                result = Error(msg=str(exc), item=self)
        return result

    def __str__(self):
        if self.isfunction:
            return "TestItem from %s.%s" % (self.module.__name__,
                                            self.callable.__name__)
        else:
            return "TestItem from %s.%s.%s" % (self.module.__name__,
                   self.cls.__name__, self.callable.__name__)

    def __repr__(self):
        return "<%s at %#x>" % (str(self), id(self))


class TestSuite:
    """Represent a collection of test items."""
    def __init__(self):
        self.reset()

    def reset(self):
        """
        Clear this TestSuite instance from all stored items and
        test results.
        """
        self.items = []
        self.last_results = {}

    #
    # get lists of TestItems from a dictionary, a module, or a directory tree
    #
    def items_from_dict(self, dict_, module=None):
        """
        Return a list of TestItems as extracted from the given dictionary
        dict_. The keys of the dictionary are names of objects, the values
        are the corresponding objects. Think of the value returned by the
        builtin function globals.

        You may pass in a module object via the optional argument module.
        If the argument is present, it will be included in the TestItems.
        Else, the __main__ module will be used.
        """
        if module is None:
            module = __import__('__main__')
        items = []
        # scan the values for test functions, and for classes derived
        # from TestCase
        for obj in dict_.values():
            # find TestCase classes and methods within them
            if inspect.isclass(obj) and issubclass(obj, TestCase):
                # we found a TestCase class, now scan it for test methods
                for obj2 in vars(obj).values():
                    # inspect.ismethod doesn't seem to work here
                    if inspect.isfunction(obj2) and \
                      obj2.__name__.startswith("test"):
                        items.append(TestItem(module=module, cls=obj,
                                              callable=obj2))
            # find test functions
            elif (callable(obj) and hasattr(obj, '__name__') and
                  obj.__name__.startswith('test_')):
                items.append(TestItem(module, callable=obj))
        return items

    def items_from_module(self, module):
        """Return a list of TestItems read from the given module."""
        return self.items_from_dict(vars(module), module=module)

    def _module_from_modpath(self, modpath):
        """
        Return a module object derived from the module path
        (e. g. "pypy.module.builtin.test.test_minmax").
        """
        # This __import__ call is only used to ensure that the module
        # is present in sys.modules. Unfortunately, the module returned
        # from the __import__ function doesn't correspond to the last
        # component of the module path but the first. In the example
        # listed in the docstring we thus would get the pypy module
        # (i. e. package), not the test_minmax module.
        __import__(modpath)
        return sys.modules[modpath]

    def items_from_dir(self, dirname, filterfunc=None, recursive=True):
        """
        Return a list of TestItems found by reading the directory denoted
        by dirname. Find all test modules in it. Test modules are files that
        comply with the shell pattern "test_*.py".

        filterfunc is a callable that can be used to filter the test
        modules by module path. By default, all test modules are used.

        If recursive is true, which is the default, find all test modules
        by scanning the start directory recursively.
        """
        items = []
        dirname = vpath.getlocal(dirname)

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
                    module_items = self.items_from_module(module)
                except:
                    print >> sys.stderr, \
                          "Warning: can't load module %s" % modpath
                    raise
                else:
                    items.extend(module_items)
        return items

    #
    # init TestSuite instance from a dictionary, a module, or a directory tree
    #
    def init_from_dict(self, dict_, module=None):
        self.reset()
        self.items = self.items_from_dict(dict_, module=module)

    def init_from_module(self, module):
        self.reset()
        self.items = self.items_from_module(module)

    def init_from_dir(self, dirname, filterfunc=None, recursive=True):
        self.reset()
        self.items = self.items_from_dir(dirname, filterfunc=None,
                                         recursive=True)

    #
    # running tests and getting results
    #
    def result_generator(self,
                         classify=lambda result: result.item.module.__name__):
        """
        Return a generator to get the test result for each test item.

        The optional argument classify must be callable which accepts
        a TestResult instance as the argument and returns something
        that can be used as a dictionary key.

        During the iteration over the generator, the TestSuite object
        will contain a dictionary named lastresult which maps these
        keys to a list of TestResult objects that correspond to the key.
        """
        self.last_results = {}
        for item in self.items:
            result = item.run()
            key = classify(result)
            self.last_results.setdefault(key, []).append(result)
            yield result

    def run(self):
        """
        Run all the test items and return a list of the results. After
        that, the results are available via the attribute last_results.
        """
        # perform all the tests by using the existing generator; discard
        # the results; they are then available via self.last_results
        return [result for result in self.result_generator()]


def _print_results(suite):
    """Print results for the items in a test suite."""
    # iterate over tests and collect data
    for result in suite.result_generator():
        if result.traceback is None:
            continue
        print 79 * '-'
        # print a line with the qualified name of the bad callable
        item = result.item
        if result.item.isfunction:
            print "%s.%s: %s" % (item.module.__name__, item.callable.__name__,
                                 result.name.upper())
        else:
            print "%s.%s.%s: %s" % (item.module.__name__, item.cls.__name__,
                                    item.callable.__name__, result.name.upper())
        print
        print result.formatted_traceback
    # emit a summary
    print 79 * '='
    modules = suite.last_results.keys()
    modules.sort()
    for module in modules:
        results = suite.last_results[module]
        resultstring = ''
        for result in results:
            status_char = {Success: '.', Ignored: 'i', Skipped: 's',
                           Error: 'E', Failure: 'F'}[result.__class__]
            resultstring += status_char
        print "%s [%d] %s" % (module, len(results), resultstring)

def main():
    """
    Find all tests in the current module (i. e. the module from which this
    function is called), execute them and print results.
    """
    import __main__
    from pypy.tool import newtest
    suite = TestSuite()
    suite.init_from_dict(vars(__main__))
    _print_results(suite)

def test(do_selftest=False):
    # possibly ignore dummy unit tests
    if do_selftest:
        # include only selftest module
        filterfunc = lambda m: m.find("pypy.tool.testdata.") != -1
    else:
        # exclude selftest module
        filterfunc = lambda m: m.find("pypy.tool.testdata.") == -1
    # collect tests
    suite = TestSuite()
    print "Loading test modules ..."
    suite.init_from_dir(autopath.pypydir, filterfunc=filterfunc)
    _print_results(suite)


if __name__ == '__main__':
    # used to avoid subtle problems with class matching after different
    # import statements
    from pypy.tool import newtest
    newtest.test(do_selftest=True)
