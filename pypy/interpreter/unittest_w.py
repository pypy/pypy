import autopath

import os
import unittest
from pypy.interpreter import gateway

try:
    f = open(os.path.join(autopath.pypydir, 'ignore_tests.txt'))
except IOError:
    IGNORE_TESTS = []
else:
    IGNORE_TESTS = [s.strip() for s in f.readlines()]
    f.close()


def make_testcase_class(space, tc_w):
    # XXX this is all a bit insane (but it works)

    # collect the test methods into a dictionary
    w = space.wrap
    w_dict = space.newdict([])
    for name in dir(AppTestCase):
        if ( name.startswith('assert') or name.startswith('fail')
             and name != 'failureException'):
            fn = gateway.app2interp(getattr(tc_w, name).im_func, name)
            space.setitem(w_dict, w(name), w(fn))

    # space-dependent part: make an object-space-level dictionary
    # and use it to build the class.
    space.setitem(w_dict, w('failureException'), space.w_AssertionError)
    w_tc = space.call_function(space.w_type,
                               w('TestCase'),
                               space.newtuple([]),
                               w_dict)
    return space.call_function(w_tc)


class WrappedFunc(object):

    def __init__(self, testCase, testMethod):
        self.testCase = testCase
        self.testMethod = testMethod

    def __call__(self):
        space = self.testCase.space

        w_tc_attr = 'tc-attr-hacky-thing'
        if hasattr(space, w_tc_attr):
            w_tc = getattr(space, w_tc_attr)
        else:
            w_tc = make_testcase_class(space, self.testCase)
            setattr(space, w_tc_attr, w_tc)

        f = self.testMethod.im_func
        gway = gateway.app2interp(f, f.func_name)
        gway(space, w_tc)


class IntTestCase(unittest.TestCase):
    """ enrich TestCase with wrapped-methods """
    def __init__(self, methodName='runTest'):
        self.methodName = methodName
        unittest.TestCase.__init__(self, methodName)

    def _answer(self, result, errorfn):
        id = self.id()
        for ignored in IGNORE_TESTS:
            if id.startswith(ignored):
                errorfn = result.addIgnored
        errorfn(self, self._TestCase__exc_info())

    def __call__(self, result=None):
        from pypy.tool.testit import TestSkip
        if result is None: result = self.defaultTestResult()
        result.startTest(self)
        testMethod = getattr(self, self.methodName)
        try:
            try:
                self.setUp()
            except TestSkip: 
                result.addSkip(self)
                return
            except KeyboardInterrupt:
                raise
            except:
                self._answer(result, result.addError)
                return

            ok = 0
            try:
                testMethod()
                ok = 1
            except self.failureException, e:
                self._answer(result, result.addFailure)
            except TestSkip: 
                result.addSkip(self)
                return
            except KeyboardInterrupt:
                raise
            except:
                self._answer(result, result.addError)

            try:
                self.tearDown()
            except KeyboardInterrupt:
                raise
            except:
                self._answer(result, result.addError)
                ok = 0
            if ok: result.addSuccess(self)
        finally:
            result.stopTest(self)
    

    def failUnless_w(self, w_condition, msg=None):
        condition = self.space.is_true(w_condition)
        return self.failUnless(condition, msg)

    def failIf_w(self, w_condition, msg=None):
        condition = self.space.is_true(w_condition)
        return self.failIf(condition, msg)

    def assertEqual_w(self, w_first, w_second, msg=None):
        w_condition = self.space.eq(w_first, w_second)
        condition = self.space.is_true(w_condition)
        if msg is None:
            msg = '%s != %s'%(w_first, w_second)
        return self.failUnless(condition, msg)

    def assertNotEqual_w(self, w_first, w_second, msg=None):
        w_condition = self.space.eq(w_first, w_second)
        condition = self.space.is_true(w_condition)
        if msg is None:
            msg = '%s == %s'%(w_first, w_second)
        return self.failIf(condition, msg)

    def assertRaises_w(self, w_exc_class, callable, *args, **kw):
        from pypy.interpreter.baseobjspace import OperationError
        try:
            callable(*args, **kw)
        except OperationError, e:
            self.failUnless(e.match(self.space, w_exc_class))
        else:
            self.fail('should have got an exception')

    def assertWRaises_w(self, w_exc_class, w_callable, *args_w, **kw_w):
        from pypy.objspace.std.objspace import OperationError
        try:
            self.space.call_function(w_callable, *args_w, **kw_w)
        except OperationError, e:
            self.failUnless(e.match(self.space, w_exc_class))
        else:
            self.fail('should have got an exception')


class AppTestCase(IntTestCase):
    def __call__(self, result=None):
        if type(getattr(self, self.methodName)) != WrappedFunc:
            setattr(self, self.methodName,
                WrappedFunc(self, getattr(self, self.methodName)))
        return IntTestCase.__call__(self, result)
        
    def setUp(self):
        from pypy.tool import testit
        self.space = testit.objspace()
