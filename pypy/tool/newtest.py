import autopath
import inspect
import os
import sys
import cStringIO as StringIO
import traceback
import unittest
import vpath

#TODO
# - add support for ignored/skipped tests
# - support TestItem.run with different object spaces

class TestStatus:
    def __init__(self, name, longstring, shortstring):
        self.name = name
        self.longstring = longstring
        self.shortstring = shortstring

    def __str__(self):
        return self.longstring

# named constants for test result status values
SUCCESS = TestStatus('success', 'success', '.')
ERROR = TestStatus('error', 'ERROR', 'E')
FAILURE = TestStatus('failure', 'FAILURE', 'F')
IGNORED = TestStatus('ignored', 'ignored', 'i')
SKIPPED = TestStatus('skipped', 'skipped', 's')


class TestResult:
    """Represent the result of a run of a test item."""
    def __init__(self, item):
        self.item = item
        # one of None, SUCCESS, ERROR, FAILURE, IGNORED, SKIPPED (see above)
        self.status = None
        # traceback object for errors and failures, else None
        self.traceback = None
        # formatted traceback (a string)
        self.formatted_traceback = None

    def _setstatus(self, statuscode):
        self.status = statuscode
        self.excinfo = sys.exc_info()
        self.traceback = self.excinfo[2]
        # store formatted traceback
        output = StringIO.StringIO()
        args = self.excinfo + (None, output)
        traceback.print_exception(*args)
        self.formatted_traceback = output.getvalue().strip()


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

        # prepare result object
        result = TestResult(self)
        result.status = None

        # prepare test case class and test method
        methodname = self.method.__name__
        testobject = self.cls(methodname)
        testmethod = getattr(testobject, methodname)

        if pretest is not None:
            pretest(self)
        try:
            try:
                testobject.setUp()
            except KeyboardInterrupt:
                raise
            except:
                result._setstatus(ERROR)
                return

            try:
                testmethod()
                result.status = SUCCESS
            except AssertionError:
                result._setstatus(FAILURE)
            except KeyboardInterrupt:
                raise
            except:
                result._setstatus(ERROR)

            try:
                testobject.tearDown()
            except KeyboardInterrupt:
                raise
            except:
                result._setstatus(ERROR)
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
                    print "skipping testfile (failed loading it)", modpath
                    raise
                else:
                    self.items.extend(items)

    def testresults(self):
        """Return a generator to get the test result for each test item."""
        for item in self.items:
            yield item.run()


if __name__ == '__main__':
    ts = TestSuite()
    ts.initfromdir(".")
    for res in ts.testresults():
        print 75 * '-'
        print "%s: %s" % (res.item, res.status)
        if res.traceback:
            print '-----'
            print res.formatted_traceback

