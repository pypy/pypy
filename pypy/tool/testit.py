import autopath
import os, sys, unittest, re, warnings, unittest, traceback, StringIO
import fnmatch
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

        fm = getattr(self, 'frommodule', '')

        if fm and Options.verbose == 0:
            sys.stderr.write('\n%s [%d]' %(fm, count))
        result = unittest.TestSuite.__call__(self, result)
        return result

    def addTest(self, test, frommodule=None):
        if test.countTestCases() > 0:
            test.frommodule = frommodule
            unittest.TestSuite.addTest(self, test)

    def __nonzero__(self):
        return self.countTestCases() > 0

# register MyTestSuite to unittest
unittest.TestLoader.suiteClass = MyTestSuite


class MyTestResult(unittest.TestResult):
    def __init__(self):
        unittest.TestResult.__init__(self)
        self.successes = []

    def addError(self, test, err):
        # XXX not nice:
        from pypy.interpreter.baseobjspace import OperationError
        if isinstance(err[1], OperationError) and test.space.full_exceptions:
            if err[1].match(test.space, test.space.w_AssertionError):
                self.addFailure(test, err)
                return
        unittest.TestResult.addError(self, test, err)

    def addSuccess(self, test):
        self.successes.append(test)

    def addSkip(self, test):
        self.testsRun -= 1

    def addIgnored(self, test, err):
        pass


class MyTextTestResult(unittest._TextTestResult):
    ignored = 0
    trace_information = []

    def record_trace(self, test):
        # XXX hack for TraceObjSpace
        try:
            result = test.space.getresult()
        except AttributeError:
            pass
        else:
            self.trace_information.append((test, result))
            test.space.settrace()

    def addError(self, test, err):
        self.record_trace(test)
        from pypy.interpreter.baseobjspace import OperationError
        if isinstance(err[1], OperationError) and test.space.full_exceptions:
            if err[1].match(test.space, test.space.w_AssertionError):
                self.addFailure(test, err)
                return
        unittest._TextTestResult.addError(self, test, err)
        self.errors[-1] = (test, sys.exc_info())

    def addFailure(self, test, err):
        self.record_trace(test)
        unittest._TextTestResult.addFailure(self, test, err)
        self.failures[-1] = (test, sys.exc_info())

    def addSkip(self, test):
        self.testsRun -= 1
        if self.showAll:
            self.stream.writeln("skipped")
        elif self.dots:
            self.stream.write('s')

    def addIgnored(self, test, err):
        self.ignored += 1
        if self.showAll:
            self.stream.writeln("ignored")
        elif self.dots:
            self.stream.write('i')

    def interact(self):
        #efs = self.errors + self.failures
        #from pypy.tool.testitpm import TestPM
        #c = TestPM(efs)
        #c.cmdloop()
        for test, (exc_type, exc_value, exc_tb) in self.errors + self.failures:
            import pdb; pdb.post_mortem(exc_tb)

    def printErrors(self):
        if self.trace_information:
            from pypy.tool.traceop import print_result
            for test, trace in self.trace_information:
                print_result(test.space, trace)
            sys.stdout.flush()
        if Options.interactive:
            print
            if self.errors or self.failures:
                self.interact()
        else:
            unittest._TextTestResult.printErrors(self)

    def printErrorList(self, flavour, errors):
        from pypy.interpreter.baseobjspace import OperationError
        for test, err in errors:
            t1, t2 = '', ''
            if not Options.quiet:
                self.stream.writeln(self.separator1)
                self.stream.writeln("%s: %s" % (flavour,self.getDescription(test)))
                self.stream.writeln(self.separator2)
                t1 = ''.join(traceback.format_exception(*err))
            if isinstance(err[1], OperationError) and \
              test.space.full_exceptions:
                if not Options.quiet:
                    t2 = '\nand at app-level:\n\n'
                sio = StringIO.StringIO()
                err[1].print_application_traceback(test.space, sio)
                t2 += sio.getvalue()
            self.stream.writeln("%s" % (t1 + t2,))


class CtsTestRunner:
    def _methodname(self, result):
        "Return a normalized form of the method name for result."
        # use private method, id() is not enough for us
        return "%s.%s" % (result.__class__.__name__,
                          result._TestCase__testMethodName)

    def run(self, test):
        import pickle

        result = MyTestResult()
        try:
            # discard output of test or suite
            sys.stdout = sys.stderr = StringIO.StringIO()
            test(result)
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

        # load status from previous run if available
        if os.path.exists('testcts.pickle'):
            oldstatus = pickle.load(open('testcts.pickle', 'r'))
        else:
            oldstatus = {}

        # store status from this run
        status = {}
        for e in result.errors:
            name = self._methodname(e[0])
            status[name] = 'ERROR'
        for f in result.failures:
            name = self._methodname(f[0])
            status[name] = 'FAILURE'
        for s in result.successes:
            name = self._methodname(s)
            status[name] = 'success'

        # compare statuses from previous and this run
        oldmethods = oldstatus.keys()
        methods = status.keys()
        allmethods = dict([(m, 1) for m in oldmethods+methods]).keys()
        allmethods.sort()

        for m in allmethods:
            is_old = (m in oldstatus)
            is_new = (m in status)
            # case: test was run previously _and_ now
            if is_old and is_new:
                old = oldstatus[m]
                new = status[m]
                if old != new:
                    # print all transitions
                    print "%s has changed from %s to %s" % (m, old, new)
                elif new != "success":
                    # print old statuses only if they weren't successes
                    print "%s remains a %s" % (m, new)
            # case: test was run previously but not now
            elif is_old and not is_new:
                print "%s was a %s but not run this time" % (m, oldstatus[m])
                # retain status from previous run
                status[m] = oldstatus[m]
            # case: test was not run previously but now
            elif not is_old and is_new:
                # print nothing, just keep the old status
                pass

        # save result from this run
        pickle.dump(status, open('testcts.pickle', 'w'))

        return result


class MyTextTestRunner(unittest.TextTestRunner):
    def run(self, test):
        result = unittest.TextTestRunner.run(self, test)
        if result.ignored:
            self.stream.writeln("(ignored=%d)" % result.ignored)
        return result

    def _makeResult(self):
        return MyTextTestResult(self.stream, self.descriptions, self.verbosity)


def testsuite_from_main():
    """Return test modules from __main__."""
    loader = unittest.TestLoader()
    m = __import__('__main__')
    return loader.loadTestsFromModule(m)

def testsuite_from_dir(root, filterfunc=None, recursive=0, loader=None):
    """
    Return test modules that optionally match filterfunc.

    All files matching the glob-pattern "test_*.py" are considered.
    Additionally, their fully qualified python module path has
    to be accepted by filterfunc (if it is not None).
    """
    from std import path 
    root = path.local(root)

    if Options.verbose > 2:
        print >> sys.stderr, "scanning for test files in", root

    if loader is None:
        loader = unittest.TestLoader()

    def testfilefilter(p):
        return p.check(file=1, fnmatch='test_*.py') 
    def recfilter(p):
        return recursive and p.check(dotfile=0) 
    
    suite = unittest.TestLoader.suiteClass()

    for testfn in root.visit(testfilefilter, recfilter):
        # strip the leading pypy directory and the .py suffix
        modpath = str(testfn)[len(autopath.pypydir)+1:-3]
        modpath = 'pypy.' + modpath.replace(os.sep, '.')
        if (filterfunc is None) or filterfunc(modpath):
            try:
                subsuite = loader.loadTestsFromName(modpath)
            except:
                print "skipping testfile (failed loading it)", modpath
            else:
                suite.addTest(subsuite, modpath)
    return suite

class Options(option.Options):
    testreldir = 0
    runcts = 0
    spacename = ''
    individualtime = 0
    interactive = 0
    trace_flag = 0
    #XXX what's the purpose of this?
    def ensure_value(*args):
        return 0
    ensure_value = staticmethod(ensure_value)
    quiet = 0

class TestSkip(Exception):
    pass

def objspace(name='', new_flag=False):
    if name and Options.spacename and name != Options.spacename:
        raise TestSkip
    if new_flag:
        space = option.objspace(name, _spacecache={})    
    else:
        space = option.objspace(name)        
    if Options.trace_flag:
        # XXX This really sucks as a means to turn on tracing for a sole unit
        # test (esp at app level).  I can't see an obvious way to do this
        # better.  Don't think it is worth any mental energy given the new
        # testing framework is just around the corner.
        from pypy.objspace.trace import create_trace_space
        create_trace_space(space)
        space.settrace()
    return space

def new_objspace(name=''):
    return objspace(name=name, new_flag=True)

class RegexFilterFunc:
    """
    Stateful function to filter included/excluded strings via
    a regular expression.

    An 'excluded' regular expressions has a '%' prependend.
    """
    def __init__(self, *regex):
        self.exclude = []
        self.include = []
        for x in regex:
            if x.startswith('%'):
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
        '-p', action="store_true", dest="trace_flag",
        help="augment object space with tracing capabilities"))
    options.append(make_option(
        '-r', action="store_true", dest="testreldir",
        help="gather only tests relative to current dir"))
    options.append(make_option(
        '-t', action="store_true", dest="individualtime",
        help="time each test individually"))
    options.append(make_option(
        '-i', action="store_true", dest="interactive",
        help="enter an interactive mode on failure or error"))
    options.append(make_option(
        '-q', action="store_true", dest="quiet",
        help="suppress some information (e.g. interpreter level exceptions)"))
    options.append(make_option(
        '-c', action="store_true", dest="runcts",
        help="run CtsTestRunner (discards output and prints report "
             "after testing)"))
    return options

def run_tests(suite):
    for spacename in Options.spaces or ['']:
        run_tests_on_space(suite, spacename)

def run_tests_on_space(suite, spacename=''):
    """Run the suite on the given space."""
    if Options.runcts:
        runner = CtsTestRunner() # verbosity=Options.verbose+1)
    else:
        runner = MyTextTestRunner(verbosity=Options.verbose+1)

    if spacename:
        Options.spacename = spacename

    warnings.defaultaction = Options.showwarning and 'default' or 'ignore'
    #print >> sys.stderr, "running tests via", repr(objspace())
    runner.run(suite)

def main(root=None):
    """
    Test everything in the __main__ or in the given root
    directory (recursive).
    """
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
    if Options.verbose:
        from pypy.tool.udir import udir
        print "testdata (unittestsession) directory was:", str(udir)


if __name__ == '__main__':
    # test all of pypy
    main(autopath.pypydir)
