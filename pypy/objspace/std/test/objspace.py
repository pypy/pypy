import new

class FailedToImplement(Exception):
    pass

class OperationError(Exception):
    pass

class FakeRegister:
    def register(self,*argl,**argv):
        pass

class CallWrapper:
    def __init__(self,module):
        self._module = module

    def call(self,space,methodname,attributes):
        return getattr(self._module,methodname)(*attributes)
class W_NoneObject:pass

class W_BoolObject:pass

class WrapClass:
    def __init__(self,value):
        self.value = value

class ObjSpace:
    add = FakeRegister()
    sub = FakeRegister()
    mul = FakeRegister()
    pow = FakeRegister()
    pos = FakeRegister()
    neg = FakeRegister()
    not_ = FakeRegister()
    invert = FakeRegister()
    truediv = FakeRegister()
    floordiv = FakeRegister()
    div = FakeRegister()
    mod = FakeRegister()
    lshift = FakeRegister()
    rshift = FakeRegister()
    and_ = FakeRegister()
    xor = FakeRegister()
    or_ = FakeRegister()
    oct = FakeRegister()
    hex = FakeRegister()
    ord = FakeRegister()
    float = FakeRegister()
    repr = FakeRegister()
    str = FakeRegister()
    compare = FakeRegister()
    hash = FakeRegister()
    divmod = FakeRegister()
    abs = FakeRegister()
    nonzero = FakeRegister()
    coerce = FakeRegister()
    int = FakeRegister()
    long = FakeRegister()
    float = FakeRegister()

    w_TypeError = "w_TypeError"
    w_ValueError = "w_ValueError"
    w_OverflowError = "w_OverflowError"
    w_ZeroDivisionError = "w_ZeroDivisionError"

    def wrap(self,item):
        return WrapClass(item)

    def unwrap(self,item):
        return item.value

    def AppFile(self,name):
        thismod = new.module(name+'_app')
        thisglobals = {}
        thislocals = {}
        try:
            execfile(name+'_app.py',thismod.__dict__)
        except:
            try:
                execfile(name+'-app.py',thismod.__dict__)
            except IOError:
                execfile(name+'.app.py',thismod.__dict__)
        #namespace = thislocals.update(thisglobals)
        ret = CallWrapper(thismod)
        return ret

    def newtuple(self, tuplelist):
        return self.wrap(tuple(tuplelist))

    def newdouble(self, thisdouble):
        return self.wrap(thisdouble)

    def newlong(self, thislong):
        return self.wrap(thislong)

    def newbool(self, thisbool):
        return self.wrap(thisbool)

StdObjSpace = ObjSpace()

if __name__ == '__main__':
    space = ObjSpace()
    handle = space.applicationfile('test')
    handle.call(space,'test',[2])
