import py
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.test_llinterp import gengraph, interpret, interpret_raises

class BaseRtypingTest(object):

    FLOAT_PRECISION = 8

    def gengraph(self, func, argtypes=[], viewbefore='auto', policy=None,
             backendopt=False, config=None):
        return gengraph(func, argtypes, viewbefore, policy, type_system=self.type_system,
                        backendopt=backendopt, config=config)
    
    def interpret(self, fn, args, **kwds):
        return interpret(fn, args, type_system=self.type_system, **kwds)

    def interpret_raises(self, exc, fn, args, **kwds):
        return interpret_raises(exc, fn, args, type_system=self.type_system, **kwds)

    def float_eq(self, x, y):
        return x == y

    def float_eq_approx(self, x, y):
        maxError = 10**-self.FLOAT_PRECISION
        if abs(x-y) < maxError:
            return True

        if abs(y) > abs(x):
            relativeError = abs((x - y) / y)
        else:
            relativeError = abs((x - y) / x)

        return relativeError < maxError

    def is_of_type(self, x, type_):
        return type(x) is type_

    def _skip_llinterpreter(self, reason, skipLL=True, skipOO=True):
        if skipLL and self.type_system == 'lltype':
            py.test.skip("lltypesystem doesn't support %s, yet" % reason)        
        if skipOO and self.type_system == 'ootype':
            py.test.skip("ootypesystem doesn't support %s, yet" % reason)    

class LLRtypeMixin(object):
    type_system = 'lltype'

    def ll_to_string(self, s):
        if not s:
            return None
        return ''.join(s.chars)

    def ll_to_unicode(self, s):
        return u''.join(s.chars)

    def string_to_ll(self, s):
        from pypy.rpython.module.support import LLSupport        
        return LLSupport.to_rstr(s)

    def unicode_to_ll(self, s):
        from pypy.rpython.module.support import LLSupport        
        return LLSupport.to_runicode(s)

    def ll_to_list(self, l):
        r = []
        items = l.ll_items()
        for i in range(l.ll_length()):
            r.append(items[i])
        return r

    def ll_unpack_tuple(self, t, length):
        return tuple([getattr(t, 'item%d' % i) for i in range(length)])

    def get_callable(self, fnptr):
        return fnptr._obj._callable

    def class_name(self, value):
        return "".join(value.super.typeptr.name)[:-1]

    def read_attr(self, value, attr_name):
        value = value._obj
        while value is not None:
            attr = getattr(value, "inst_" + attr_name, None)
            if attr is None:
                value = value._parentstructure()
            else:
                return attr
        raise AttributeError()

    def is_of_instance_type(self, val):
        T = lltype.typeOf(val)
        return isinstance(T, lltype.Ptr) and isinstance(T.TO, lltype.GcStruct)


class OORtypeMixin(object):
    type_system = 'ootype'

    def ll_to_string(self, s):
        return s._str

    ll_to_unicode = ll_to_string

    def string_to_ll(self, s):
        from pypy.rpython.module.support import OOSupport        
        return OOSupport.to_rstr(s)

    def unicode_to_ll(self, u):
        from pypy.rpython.module.support import OOSupport
        return OOSupport.to_runicode(u)

    def ll_to_list(self, l):
        if hasattr(l, '_list'):
            return l._list[:]
        return l._array[:]

    def ll_unpack_tuple(self, t, length):
        return tuple([getattr(t, 'item%d' % i) for i in range(length)])

    def get_callable(self, sm):
        return sm._callable

    def class_name(self, value):
        return ootype.dynamicType(value)._name.split(".")[-1] 

    def read_attr(self, value, attr):
        value = ootype.oodowncast(ootype.dynamicType(value), value)
        return getattr(value, "o" + attr)

    def is_of_instance_type(self, val):
        T = lltype.typeOf(val)
        return isinstance(T, ootype.Instance)
