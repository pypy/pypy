import autopath
import inspect
import os
import sys
import cStringIO as StringIO
import traceback
import unittest
import vpath

#TODO
# - add support for ignored tests
# - support TestItem.run with different object spaces
# - perhaps we have to be able to compare TestResult and TestItem values
#   which were pickled (see -c option of current test_all.py)

#
# TestResult class family
#
class TestResult:
    """Abstract class representing the outcome of a test."""
    def __init__(self, item):
        self.item = item
        self.name = self.__class__.__name__
        self.traceback = None

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
    def __init__(self, item):
        TestResult.__init__(self, item)
        self.setexception()

    def __eq__(self, other):
        return TestResult.__eq__(self, other) and \
               self.formatted_traceback == other.formatted_traceback

    def setexception(self):
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
    """Represent a single test method from a TestCase class."""
    def __init__(self, module, cls, testmethod):
        self.file = inspect.getsourcefile(module)
        self.module = module
        self.cls = cls
        self.method = testmethod
        #XXX inspect.getsourcelines may fail if the file path stored
        #  in a module's pyc/pyo file doesn't match the py file's
        #  actual location. This can happen if a py file, together with
        #  its pyc/pyo file is moved to a new location. See Python
        #  bug "[570300] inspect.getmodule symlink-related failure":
        #  http://sourceforge.net/tracker/index.php?func=detail&aid=570300&group_id=5470&atid=105470
        lines, self.lineno = inspect.getsourcelines(testmethod)
        # removing trailing newline(s) but not the indentation
        self.source = ''.join(lines).rstrip()

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
          (self.method.__name__ == other.method.__name__):
            return True
        return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return id(self.module) ^ id(self.cls)

    def run(self, pretest=None, posttest=None):
        """
        Run this TestItem and return a corresponding TestResult object.

        pretest, if not None, is a callable which is called before
        running the setUp method of the TestCase class. It is passed
        the this TestItem instance as the argument.

        Similarly, posttest is called after running the TestCase
        class's tearDown method (or after the test method, if that
        doesn't complete successfully). Like for pretest, the
        callable gets the TestItem instance as only argument.
        """
        # Note on pretest and posttest: I discarded the idea to
        # supply this functionality by having hypothetical methods
        # pretest and posttest overwritten in derived classes. That
        # approach would require to support a factory class for test
        # items in TestSuite. I wanted to avoid this.

        # credit: adapted from Python's unittest.TestCase.run

        # prepare test case class and test method
        methodname = self.method.__name__
        testobject = self.cls(methodname)
        testmethod = getattr(testobject, methodname)

        if pretest is not None:
            pretest(self)
        try:
            #XXX possibly will have to change
            from pypy.tool import test
            try:
                testobject.setUp()
            except KeyboardInterrupt:
                raise
            except:
                return Error(self)

            try:
                testmethod()
                result = Success(self)
            except KeyboardInterrupt:
                raise
            except AssertionError:
                result = Failure(self)
            except:
                result = Error(self)

            try:
                testobject.tearDown()
            except KeyboardInterrupt:
                raise
            except:
                # if we already had an exception in the test method,
                # don't overwrite it
                if not isinstance(result, TestResultWithTraceback):
                    result = Error(self)
        finally:
            if posttest is not None:
                posttest(self)
        return result

    def __str__(self):
        return "TestItem from %s.%s.%s" % (self.module.__name__,\
               self.cls.__name__, self.method.__name__)

    def __repr__(self):
        return "<%s at %#x>" % (str(self), id(self))


class TestSuite:
    """Represent a collection of test items."""
    def __init__(self):
        self.items = []
        self.lastresult = {}

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

    def _items_from_module(self, module):
        """Return a list of TestItems read from the given module."""
        items = []
        # scan the module for classes derived from unittest.TestCase
        for obj in vars(module).values():
            if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
                # we found a TestCase class, now scan it for test methods
                for obj2 in vars(obj).values():
                    # inspect.ismethod doesn't seem to work here
                    if inspect.isfunction(obj2) and \
                      obj2.__name__.startswith("test"):
                        items.append(TestItem(module, obj, obj2))
        return items

    def initfromdir(self, dirname, filterfunc=None, recursive=True):
        """
        Init this suite by reading the directory denoted by dirname,
        then find all test modules in it. Test modules are files that
        comply with the shell pattern shell_pattern "test_*.py".

        filterfunc is a callable that can be used to filter the test
        modules by module path. By default, all test modules are used.

        If recursive is true, which is the default, find all test modules
        by scanning the start directory recursively.
        """
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
                    items = self._items_from_module(module)
                except:
                    print >> sys.stderr, \
                          "Warning: can't load module %s" % modpath
                else:
                    self.items.extend(items)

    def testresults(self, classify=lambda result: result.item.module.__name__):
        """
        Return a generator to get the test result for each test item.

        The optional argument classify must be callable which accepts
        a TestResult instance as the argument and returns something
        that can be used as a dictionary key.

        During the iteration over the generator, the TestSuite object
        will contain a dictionary named lastresult which maps these
        keys to a list of TestResult objects that correspond to the key.
        """
        self.lastresults = {}
        for item in self.items:
            result = item.run()
            key = classify(result)
            self.lastresults.setdefault(key, []).append(result)
            yield result

#
# demonstrate test framework usage
#
def main(skip_selftest=True):
    # possibly ignore dummy unit tests
    if skip_selftest:
        filterfunc = lambda m: m.find("pypy.tool.testdata.") == -1
    else:
        filterfunc = lambda m: True
    # collect tests
    ts = TestSuite()
    print "Loading test modules ..."
    ts.initfromdir(autopath.pypydir, filterfunc=filterfunc)
    # iterate over tests and collect data
    for res in ts.testresults():
        if res.traceback is None:
            continue
        print 79 * '-'
        print "%s.%s: %s" % (res.item.module.__name__, res.item.method.__name__,
                             res.name.upper())
        print
        print res.formatted_traceback
    # emit a summary
    print 79 * '='
    modules = ts.lastresults.keys()
    modules.sort()
    for module in modules:
        results = ts.lastresults[module]
        resultstring = ''
        for result in results:
            statuschar = {Success: '.', Ignored: 'i', Skipped: 's',
                          Error: 'E', Failure: 'F'}[result.__class__]
            resultstring += statuschar
        print "%s [%d] %s" % (module, len(results), resultstring)


if __name__ == '__main__':
    main()
