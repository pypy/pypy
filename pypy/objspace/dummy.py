from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.module import Module
from pypy.interpreter.error import OperationError

class W_Obj(W_Root):
    
    def is_true(self):
        return True

    def str_w(self, space):
        raise OperationError(space.w_TypeError,space.wrap("!")) 

    def int_w(self, space):
        raise OperationError(space.w_TypeError,space.wrap("!")) 

    def float_w(self, space):
        raise OperationError(space.w_TypeError,space.wrap("!")) 

    def unwrap(self, space):
        raise OperationError(space.w_TypeError,space.wrap("!")) 

class W_Str(W_Obj):
    def __init__(self, s):
        self.s = s

    def is_true(self):
        return self.s != ""

    def str_w(self, space):
        return self.s

    def unwrap(self, space):
        return self.s

class W_Int(W_Obj):
    def __init__(self, i):
        self.i = i

    def is_true(self):
        return self.i != 0

    def int_w(self, space):
        return self.i

    def unwrap(self, space):
        return self.i

class W_None(W_Obj):
    
    def unwrap(self, space):
        return None

class W_Special(W_Obj):
    def __init__(self, spec):
        self.spec = spec


class DummyObjSpace(ObjSpace):

    def __init__(self):
        """NOT_RPYTHON"""
        self.builtin    = Module(self, self.wrap('__builtin__'), self.wrap({}))
        def pick_builtin(w_globals):
            return self.builtin
        self.builtin.pick_builtin = pick_builtin
        self.sys    = Module(self, self.wrap('sys'), self.wrap({}))
        self.sys.recursionlimit = 1000

        self.w_None = W_None()
        self.w_NotImplemented = W_Special(NotImplemented)
        self.w_Ellpisis = W_Special(Ellipsis)
        self.w_False = self.wrap(0)
        self.w_True = self.wrap(1)

        for en in ObjSpace.ExceptionTable:
            setattr(self, 'w_'+en, self.wrap(en))

    for n, symbol, arity, ign in ObjSpace.MethodTable+[('newdict',"",1,[]), ('newtuple',"",1,[]), ('newslice',"",3,[]), ]:
        source = ("""if 1:
        def %s(self, %s):
            return W_Obj()
""" % (n, ', '.join(["w_a%d" % i for i in range(arity)])))
        #print source
        exec source

    del n, symbol, arity, ign, i
        
    def wrap(self, obj):
        if obj is None:
            return self.w_None
        if isinstance(obj, str):
            return W_Str(obj)
        if isinstance(obj, int):
            return W_Int(obj)
        return W_Obj()
    wrap._specialize_ = "argtypes"

    def call_args(self, w_obj, args):
        return W_Obj()
    
    def is_true(self, w_obj):
        return w_obj.is_true()

    def str_w(self, w_obj):
        return w_obj.str_w(self)

    def int_w(self, w_obj):
        return w_obj.int_w(self)

    def float_w(self, w_obj):
        return w_obj.float_w(self)
                     
    def unwrap(self, w_obj):
        return w_obj.unwrap(self)


if __name__ == '__main__':
  dummy_space = DummyObjSpace()
  print dummy_space.eval("a+b",dummy_space.wrap({'a': 1,'b': 2}),dummy_space.wrap({}))
