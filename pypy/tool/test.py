import autopath
import os, sys, unittest, re, warnings, unittest, traceback, StringIO
from unittest import TestCase, TestLoader

import pypy.interpreter.unittest_w
from pypy.tool.optik import make_option
from pypy.tool import optik, option, ppdb

IntTestCase = pypy.interpreter.unittest_w.IntTestCase
AppTestCase = pypy.interpreter.unittest_w.AppTestCase
TestCase = IntTestCase

class MyTestSuite(unittest.TestSuite):
    def __call__(self, result):
        """ execute the tests, invokes underlying unittest.__call__"""

        count = self.countTestCases()
        if not count:
            return result

        fm = getattr(self, 'frommodule','')

        if fm and Options.verbose==0:
            sys.stderr.write('\n%s [%d]' %(fm, count))
        result = unittest.TestSuite.__call__(self, result)
        return result

    def addTest(self, test, frommodule=None):
        if test.countTestCases()>0:
            test.frommodule = frommodule
            unittest.TestSuite.addTest(self, test)

    def __nonzero__(self):
        return self.countTestCases()>0


# register MyTestSuite to unittest
unittest.TestLoader.suiteClass = MyTestSuite

class MyTestResult(unittest.TestResult):
    def __init__(self):
        unittest.TestResult.__init__(self)
        self.successes = []
    def addError(self, test, err):
        # XXX not nice:
        from pypy.interpreter.baseobjspace import OperationError
        if isinstance(err[1], OperationError):
            if err[1].match(test.space, test.space.w_AssertionError):
                self.addFailure(test, err)
                return
        unittest.TestResult.addError(self, test, err)
    def addSuccess(self, test):
        self.successes.append(test)
    def addSkip(self, test):
        self.testsRun -= 1

class MyTextTestResult(unittest._TextTestResult):
        
    def addError(self, test, err):
        from pypy.interpreter.baseobjspace import OperationError
        if isinstance(err[1], OperationError):
            if err[1].match(test.space, test.space.w_AssertionError):
                self.addFailure(test, err)
                return
        unittest._TextTestResult.addError(self, test, err)
        self.errors[-1] = (test, sys.exc_info())
        
    def addFailure(self, test, err):
        unittest._TextTestResult.addFailure(self, test, err)
        self.failures[-1] = (test, sys.exc_info())

    def addSkip(self, test):
        self.testsRun -= 1
        if self.showAll:
            self.stream.writeln("skipped")
        elif self.dots:
            self.stream.write('s')

    def interact(self):
        efs = self.errors + self.failures
        from pypy.tool.testpm import TestPM
        c = TestPM(efs)
        c.cmdloop()
        return
        def proc_input(input):
            r = int(input)
            if r < 0 or r >= len(efs):
                raise ValueError
            return r
        while 1:
            i = 0
            for t, e in efs:
                print i, t.methodName
                i += 1
            while 1:
                input = raw_input('itr> ')
                if not input:
                    return
                try:
                    r = proc_input(input)
                except ValueError:
                    continue
                else:
                    break
            s, (t, v, tb) = efs[r]
            ppdb.post_mortem(s.space, tb, v)

    def printErrors(self):
        if Options.interactive:
            print
            if self.errors or self.failures:
                self.interact()
        else:
            unittest._TextTestResult.printErrors(self)

    def printErrorList(self, flavour, errors):
        from pypy.interpreter.baseobjspace import OperationError
        for test, err in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour,self.getDescription(test)))
            self.stream.writeln(self.separator2)
            t1 = self._exc_info_to_string(err)
            t2 = ''
            if isinstance(err[1], OperationError):
                t2 = '\nand at app-level:\n\n'
                sio = StringIO.StringIO()
                err[1].print_application_traceback(test.space, sio)
                t2 += sio.getvalue()

            self.stream.writeln("%s" % (t1 + t2,))

class CtsTestRunner:
    def run(self, test):
        import pickle

        output = sys.stdout
        result = MyTestResult()
        sso = sys.stdout
        sse = sys.stderr
        try:
            sys.stdout = open('/dev/null', 'w')
            sys.stderr = open('/dev/null', 'w')
            test(result)
        finally:
            sys.stdout = sso
            sys.stderr = sse

        ostatus = {}
        if os.path.exists('testcts.pickle'):
            ostatus = pickle.load(open('testcts.pickle','r'))

        status = {}

        for e in result.errors:
            name = e[0].__class__.__name__ + '.' + \
                   e[0]._TestCase__testMethodName
            status[name] = 'ERROR'
        for f in result.failures:
            name = f[0].__class__.__name__ + '.' + \
                   f[0]._TestCase__testMethodName
            status[name] = 'FAILURE'
        for s in result.successes:
            name = s.__class__.__name__ + '.' + s._TestCase__testMethodName
            status[name] = 'success'

        keys = status.keys()
        keys.sort()

        for k in keys:
            old = ostatus.get(k, 'success')
            if k in ostatus:
                del ostatus[k]
            new = status[k]
            if old != new:
                print >>output, k, 'has transitioned from', old, 'to', new
            elif new != 'success':
                print >>output, k, "is still a", new

        for k in ostatus:
            print >>output, k, 'was a', ostatus[k], 'was not run this time'
            status[k] = ostatus[k]

        pickle.dump(status, open('testcts.pickle','w'))

        return result

class MyTextTestRunner(unittest.TextTestRunner):
    def _makeResult(self):
        return MyTextTestResult(self.stream, self.descriptions, self.verbosity)


def testsuite_from_main():
    """ return test modules from __main__

    """
    loader = unittest.TestLoader()
    m = __import__('__main__')
    return loader.loadTestsFromModule(m)

def testsuite_from_dir(root, filterfunc=None, recursive=0, loader=None):
    """ return test modules that optionally match filterfunc. 

    all files matching the glob-pattern "test_*.py" are considered.
    additionally their fully qualified python module path has
    to be accepted by filterfunc (if it is not None). 
    """
    if Options.verbose>2:
        print >>sys.stderr, "scanning for test files in", root

    if loader is None:
        loader = unittest.TestLoader()

    root = os.path.abspath(root)

    suite = unittest.TestLoader.suiteClass()
    names = os.listdir(root)
    names.sort()
    for fn in names:
        if fn.startswith('.'):
            continue
        fullfn = os.path.join(root, fn)
        if os.path.isfile(fullfn) and \
               fn.startswith('test_') and \
               fn.endswith('.py'):
            modpath = fullfn[len(autopath.pypydir)+1:-3]
            modpath = 'pypy.' + modpath.replace(os.sep, '.')
            if not filterfunc or filterfunc(modpath):
                subsuite = loader.loadTestsFromName(modpath)
                suite.addTest(subsuite, modpath)
        elif recursive and os.path.isdir(fullfn):
            subsuite = testsuite_from_dir(fullfn, filterfunc, 1, loader)
            if subsuite:
                suite._tests.extend(subsuite._tests)
    return suite

class Options(option.Options):
    testreldir = 0
    runcts = 0
    spacename = ''
    individualtime = 0
    interactive = 0
    def ensure_value(*args):
        return 0
    ensure_value = staticmethod(ensure_value)

class TestSkip(Exception):
    pass

def objspace(name=''):
    if name and Options.spacename and name != Options.spacename:
        raise TestSkip
    return option.objspace(name)

class RegexFilterFunc:
    """ stateful function to filter included/excluded strings via
    a Regular Expression. 

    An 'excluded' regular expressions has a '%' prependend. 
    """

    def __init__(self, *regex):
        self.exclude = []
        self.include = []
        for x in regex:
            if x[:1]=='%':
                self.exclude.append(re.compile(x[1:]).search)
            else:
                self.include.append(re.compile(x).search)

    def __call__(self, arg):
        for exclude in self.exclude:
            if exclude(arg):
                return
        if not self.include:
            return arg
        for include in self.include:
            if include(arg):
                return arg

def get_test_options():
    options = option.get_standard_options()
    options.append(make_option(
        '-r', action="store_true", dest="testreldir",
        help="gather only tests relative to current dir"))
    options.append(make_option(
        '-i', action="store_true", dest="individualtime",
        help="time each test individually"))
    options.append(make_option(
        '-k', action="store_true", dest="interactive",
        help="enter an interactive mode on failure or error"))
    options.append(make_option(
        '-c', action="store_true", dest="runcts",
        help="run CtsTestRunner (catches stdout and prints report "
        "after testing) [unix only, for now]"))
    return options

def run_tests(suite):
    for spacename in Options.spaces or ['']:
        run_tests_on_space(suite, spacename)

def run_tests_on_space(suite, spacename=''):
    """ run the suite on the given space """
    if Options.runcts:
        runner = CtsTestRunner() # verbosity=Options.verbose+1)
    else:
        runner = MyTextTestRunner(verbosity=Options.verbose+1)

    if spacename:
        Options.spacename = spacename

    warnings.defaultaction = Options.showwarning and 'default' or 'ignore'
    print >>sys.stderr, "running tests via", repr(objspace())
    runner.run(suite)

def main(root=None):
    """ run this to test everything in the __main__ or
    in the given root-directory (recursive)"""
    args = option.process_options(get_test_options(), Options)
    
    filterfunc = RegexFilterFunc(*args)
    if Options.testreldir:
        root = os.path.abspath('.')
    if root is None:
        suite = testsuite_from_main()
    else:
        suite = testsuite_from_dir(root, filterfunc, 1)
    if Options.individualtime and hasattr(suite, '_tests'):
        for test in suite._tests:
            if hasattr(test, '_tests'):
                for subtest in test._tests:
                    run_tests(subtest)
            else:
                run_tests(test)
    else:
        run_tests(suite)

if __name__ == '__main__':
    # test all of pypy
    main(autopath.pypydir)
