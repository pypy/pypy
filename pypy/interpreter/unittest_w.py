import autopath

import sys, os
import unittest

def wrap_func(space, func):
    # this is generally useful enough that it should probably go
    # somewhere more obvious (objspace method?)
    from pypy.interpreter import pycode
    code = pycode.PyByteCode()
    code._from_code(func.func_code)
    return space.newfunction(code, space.newdict([]),
                             space.wrap(func.func_defaults), None)

def make_testcase_class(space, tc_w):
    # XXX this is all a bit insane (but it works)
    
    from pypy.interpreter.extmodule import make_builtin_func
    w = space.wrap
    d = space.newdict([])
    space.setitem(d, w('failureException'), space.w_AssertionError)

    for name in dir(AppTestCase):
        if ( name.startswith('assert') or name.startswith('fail')
             and name != 'failureException'):
            w_func = wrap_func(space, getattr(tc_w, name).im_func)
            space.setitem(d, w(name), w_func)
    w_tc = space.call_function(space.w_type,
                               w('TestCase'),
                               space.newtuple([]),
                               d)
    return space.call_function(w_tc)


class WrappedFunc(object):

    def __init__(self, testCase, testMethod):
        self.testCase = testCase
        self.testMethod = testMethod

    def __call__(self):
        from pypy.interpreter import executioncontext
        from pypy.interpreter import pyframe
        space = self.testCase.space
        w = space.wrap

        w_tc_attr = 'tc-attr-hacky-thing'
        if hasattr(space, w_tc_attr):
            w_tc = getattr(space, w_tc_attr)
        else:
            w_tc = make_testcase_class(space, self.testCase)
            setattr(space, w_tc_attr, w_tc)

        w_f = wrap_func(space, self.testMethod.im_func)
        space.call_function(w_f, w_tc)


class IntTestCase(unittest.TestCase):
    """ enrich TestCase with wrapped-methods """

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
        from pypy.objspace.std.objspace import OperationError
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
    def __init__(self, methodName='runTest'):
        self.methodName = methodName
        unittest.TestCase.__init__(self, methodName)

    def __call__(self, result=None):
        if type(getattr(self, self.methodName)) != WrappedFunc:
            setattr(self, self.methodName,
                WrappedFunc(self, getattr(self, self.methodName)))
        return unittest.TestCase.__call__(self, result)
        
    def setUp(self):
        from pypy.tool import test
        self.space = test.objspace()
