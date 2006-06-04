import py
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.test.test_llinterp import interpret, interpret_raises

class BaseRtypingTest(object):
    def interpret(self, fn, args, **kwds):
        return interpret(fn, args, type_system=self.type_system, **kwds)

    def interpret_raises(self, exc, fn, args, **kwds):
        return interpret_raises(exc, fn, args, type_system=self.type_system, **kwds)

    def _skip_oo(self, reason):
        if self.type_system == 'ootype':
            py.test.skip("ootypesystem doesn't support %s, yet" % reason)
    

class LLRtypeMixin(object):
    type_system = 'lltype'

    def ll_to_string(self, s):
        return ''.join(s.chars)

    def string_to_ll(self, s):
        from pypy.rpython.module.support import LLSupport        
        return LLSupport.to_rstr(s)

    def ll_to_list(self, l):
        return map(None, l.ll_items())[:l.ll_length()]

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


class OORtypeMixin(object):
    type_system = 'ootype'

    def ll_to_string(self, s):
        return s._str

    def string_to_ll(self, s):
        from pypy.rpython.module.support import OOSupport        
        return OOSupport.to_rstr(s)

    def ll_to_list(self, l):
        return l._list[:]

    def get_callable(self, sm):
        return sm._callable

    def class_name(self, value):
        return ootype.dynamicType(value)._name.split(".")[-1] 

    def read_attr(self, value, attr):
        value = ootype.oodowncast(ootype.dynamicType(value), value)
        return getattr(value, "o" + attr)
