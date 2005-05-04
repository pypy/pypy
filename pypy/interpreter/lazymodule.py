from pypy.interpreter.module import Module
from pypy.interpreter.function import Function, BuiltinFunction
from pypy.interpreter import gateway 
from pypy.interpreter.error import OperationError 

import inspect

class LazyModule(Module):

    NOT_RPYTHON_ATTRIBUTES = ['loaders']
    
    def __init__(self, space, w_name): 
        """ NOT_RPYTHON """ 
        Module.__init__(self, space, w_name) 
        self.lazy = True 
        self.__class__.buildloaders()

    def get(self, name):
        space = self.space
        w_value = self.getdictvalue(space, name) 
        if w_value is None: 
            raise OperationError(space.w_AttributeError, space.wrap(name))
        return w_value 

    def call(self, name, *args_w): 
        w_builtin = self.get(name) 
        return self.space.call_function(w_builtin, *args_w)

    def getdictvalue(self, space, name): 
        try: 
            return space.getitem(self.w_dict, space.wrap(name))
        except OperationError, e: 
            if not e.match(space, space.w_KeyError): 
                raise 
            if not self.lazy: 
                return None 
            try: 
                loader = self.loaders[name]
            except KeyError: 
                return None 
            else: 
                #print "trying to load", name
                w_value = loader(space) 
                #print "loaded", w_value 
                # obscure
                func = space.interpclass_w(w_value)
                if type(func) is Function:
                    try:
                        bltin = func._builtinversion_
                    except AttributeError:
                        bltin = BuiltinFunction(func)
                        func._builtinversion_ = bltin
                    w_value = space.wrap(bltin)
                space.setitem(self.w_dict, space.wrap(name), w_value) 
                return w_value 

    def getdict(self): 
        if self.lazy: 
            space = self.space
            for name in self.loaders: 
                w_value = self.get(name)  
                space.setitem(self.w_dict, space.wrap(name), w_value) 
            self.lazy = False 
        return self.w_dict 

    def _freeze_(self):
        self.getdict()
        # hint for the annotator: Modules can hold state, so they are
        # not constant
        return False

    def buildloaders(cls): 
        """ NOT_RPYTHON """ 
        if not hasattr(cls, 'loaders'): 
            # build a constant dictionary out of
            # applevel/interplevel definitions 
            cls.loaders = loaders = {}
            pkgroot = cls.__module__
            for name, spec in cls.interpleveldefs.items(): 
                loaders[name] = getinterpevalloader(pkgroot, spec) 
            for name, spec in cls.appleveldefs.items(): 
                loaders[name] = getappfileloader(pkgroot, spec) 
    buildloaders = classmethod(buildloaders) 

def getinterpevalloader(pkgroot, spec):
    """ NOT_RPYTHON """     
    def ifileloader(space): 
        d = {'space' : space}
        # EVIL HACK (but it works, and this is not RPython :-) 
        while 1: 
            try: 
                value = eval(spec, d) 
            except NameError, ex: 
                #assert name not in d, "huh, am i looping?" 
                name = ex.args[0].split("'")[1] # super-Evil 
                try: 
                    d[name] = __import__(pkgroot+'.'+name, None, None, [name])
                except ImportError: 
                    d[name] = __import__(name, None, None, [name])
            else: 
                #print spec, "->", value
                if hasattr(value, 'func_code'):  # semi-evil 
                    return space.wrap(gateway.interp2app(value))
                assert value is not None 
                return value 
    return ifileloader 
        
applevelcache = {}
def getappfileloader(pkgroot, spec):
    """ NOT_RPYTHON """ 
    # hum, it's a bit more involved, because we usually 
    # want the import at applevel
    modname, attrname = spec.split('.')
    impbase = pkgroot + '.' + modname 
    mod = __import__(impbase, None, None, ['attrname'])
    try:
        app = applevelcache[mod]
    except KeyError:
        source = inspect.getsource(mod) 
        fn = mod.__file__
        if fn.endswith('.pyc') or fn.endswith('.pyo'):
            fn = fn[:-1]
        app = gateway.applevel(source, filename=fn)
        applevelcache[mod] = app

    def afileloader(space): 
        return app.wget(space, attrname)
    return afileloader 
