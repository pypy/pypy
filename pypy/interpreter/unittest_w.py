import sys, os
import unittest
import testtools

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
    for name in dir(AppTestCase):
        if name.startswith('assert') or name.startswith('fail'):
            if hasattr(tc_w, 'app_' + name):
                builtin_func = make_builtin_func(space, getattr(tc_w, "app_" + name),
                                                 boundmethod=True)
                space.setitem(d, w(name), builtin_func)
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
        s = self.testCase.space
        w = s.wrap

        w_tc_attr = 'tc-attr-hacky-thing'
        if hasattr(s, w_tc_attr):
            w_tc = getattr(s, w_tc_attr)
        else:
            w_tc = make_testcase_class(s, self.testCase)
            setattr(s, w_tc_attr, w_tc)

        w_f = wrap_func(s, self.testMethod.im_func)
        try:
            s.call_function(w_f, w_tc)
        except executioncontext.OperationError, oe:
            oe.print_application_traceback(s)
            import __builtin__
            w_res = s.gethelper(pyframe.appfile).call(
                "normalize_exception", [oe.w_type, oe.w_value])
            w_value = s.getitem(w_res, s.wrap(1))
            exc_name = s.getattr(s.getattr(w_value, w('__class__')),
                                 w('__name__'))
            exc_type = getattr(__builtin__, s.unwrap(exc_name))
            # it's a tad annoying we can't fake the traceback
            raise exc_type(*s.unwrap(s.getattr(w_value, w('args'))))


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
        setattr(self, self.methodName,
                WrappedFunc(self, getattr(self, self.methodName)))
        return unittest.TestCase.__call__(self, result)

    def setUp(self):
        self.space = testtools.objspace()

    def app_fail(self, w_self, w_msg=None):
        msg = self.space.unwrap(w_msg)
        self.fail(msg)

    def app_failIf(self, w_self, w_expr, w_msg=None):
        msg = self.space.unwrap(w_msg)
        self.failIf_w(w_expr)

    def app_failUnless(self, w_self, w_expr, w_msg=None):
        msg = self.space.unwrap(w_msg)
        self.failUnless_w(w_expr)

    def app_failUnlessRaises(self, w_self, w_exc_class,
                             w_callable, *args_w, **kw_w):
        self.assertWRaises_w(w_exc_class, w_callable, *args_w, **kw_w)

    def app_failUnlessEqual(self, w_self, w_first, w_second, w_msg=None):
        msg = self.space.unwrap(w_msg)
        self.assertEqual_w(w_first, w_second, msg)

    def app_failIfEqual(self, w_self, w_first, w_second, w_msg=None):
        msg = self.space.unwrap(w_msg)
        self.assertNotEqual_w(w_first, w_second, msg)

    app_assertEqual = app_assertEquals = app_failUnlessEqual

    app_assertNotEqual = app_assertNotEquals = app_failIfEqual

    app_assertRaises = app_failUnlessRaises

    app_assert_ = app_failUnless
                            
