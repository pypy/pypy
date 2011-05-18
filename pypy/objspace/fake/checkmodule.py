import re
from copy import copy
from pypy.tool.error import debug
from pypy.interpreter.argument import Arguments
from pypy.interpreter.gateway import interp2app
from pypy.rlib.nonconst import NonConstant

def my_import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def find_gateways(modname, basepath, module):
    identifier = r'[a-zA-Z0-9][a-zA-Z0-9_]*'
    r_simplename = re.compile(r'(%s)[.](%s)$' % (identifier, identifier))
    res = []
    for name in module.interpleveldefs.values():
        match = r_simplename.match(name)
        if match:
            submod_name, obj_name = match.groups()
            submod_name = '%s.%s.%s' % (basepath, modname, submod_name)
            submod = my_import(submod_name)
            obj = getattr(submod, obj_name)
            res += find_gw_in_obj(obj)
    return res

def find_gw_in_obj(obj):
    if hasattr(obj, 'typedef'):
        typedef = obj.typedef
        return [gw for gw in typedef.rawdict.values()
                if isinstance(gw, interp2app)]
    elif hasattr(obj, 'func_code'):
        return [interp2app(obj)]
    else:
        assert False

## Since the fake objspace is more a hack than a real object space, it
## happens that the annotator complains about operations that cannot
## succeed because it knows too much about the objects involved. For
## example, if it knows that a list is always empty, it will block
## each operations that tries to access that list. This is not what we
## want, because we know that with real objectspaces that operations
## will succeed.

## As a workaround, we insert dummy rpython code (the function
## dummy_rpython) that manipulates the variables in order to give
## them a more sensible annotation. This is the preferred way to solve
## the problems so far.

## If the solution above doesn't work, the alternative is to
## substitute the interpreter code with something that doesn't hurt
## the annotator. It's a very ugly hack, better solutions are welcome
## :-)


# dummy rpython code to give some variables more sensible annotations
def dummy_rpython(dummy_function):
    # to make the annotator flow-in without executing the code
    if NonConstant(False):
        dummy_function.defs_w = [None] # else the annotator would see an always empty list

def patch_pypy():
    from pypy.interpreter.baseobjspace import W_Root
    
    def descr_call_mismatch(self, space, opname, RequiredClass, args):
        from pypy.interpreter.error import OperationError
        msg = 'This message will never be displayed :-)'
        raise OperationError(space.w_TypeError, space.wrap(msg))
    W_Root.descr_call_mismatch = descr_call_mismatch


def checkmodule(modname, backend, interactive=False, basepath='pypy.module'):
    "Compile a fake PyPy module."
    from pypy.objspace.fake.objspace import FakeObjSpace, W_Object
    from pypy.translator.driver import TranslationDriver

    space = FakeObjSpace()
    space.config.translating = True
    ModuleClass = __import__(basepath + '.%s' % modname,
                             None, None, ['Module']).Module
    module = ModuleClass(space, space.wrap(modname))
    w_moduledict = module.getdict(space)

    gateways = find_gateways(modname, basepath, module)
    functions = [gw.__spacebind__(space) for gw in gateways]
    arguments = Arguments.frompacked(space, W_Object(), W_Object())
    dummy_function = copy(functions[0])

    def main(argv): # use the standalone mode not to allow SomeObject
        dummy_rpython(dummy_function)        
        for func in functions:
            func.call_args(arguments)
        return 0

    patch_pypy()
    driver = TranslationDriver()
    driver.setup(main, None)
    try:
        driver.proceed(['compile_' + backend])
    except SystemExit:
        raise
    except:
        if not interactive:
            raise
        debug(driver)
        raise SystemExit(1)
