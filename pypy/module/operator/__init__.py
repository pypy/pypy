from pypy.interpreter.mixedmodule import MixedModule 
from pypy.interpreter.error import OperationError 

class Module(MixedModule):
    """Operator Builtin Module. """

    # HACK! override loaders to be able to access different operations
    # under same name. I.e., operator.eq == operator.__eq__

    def __init__(self, space, w_name):
        def create_lambda(name, alsoname):
            return lambda space : self.getdictvalue(space, space.wrap(alsoname))
        
        MixedModule.__init__(self, space, w_name)
        for name, alsoname in self.mapping.iteritems():
            self.loaders[name] = create_lambda(name, alsoname)

    appleveldefs = {} 
    
    app_names = ['__delslice__', '__getslice__', '__repeat__', '__setslice__',
                 'countOf', 'delslice', 'getslice', 'indexOf',
                 'isMappingType', 'isNumberType', 'isSequenceType',
                 'repeat', 'setslice',
                 'attrgetter', 'itemgetter'
             ]

    for name in app_names:
        appleveldefs[name] = 'app_operator.%s' % name

    interp_names = ['index', 'abs', 'add', 'and_',
                    'concat', 'contains', 'delitem', 'div', 'eq', 'floordiv',
                    'ge', 'getitem', 'gt', 'inv',
                    'invert', 'is_', 'is_not', 'isCallable',
                    'le', 'lshift', 'lt', 'mod', 'mul',
                    'ne', 'neg', 'not_', 'or_',
                    'pos', 'pow', 'rshift', 'setitem', 'sequenceIncludes',
                    'sub', 'truediv', 'truth', 'xor']
    interpleveldefs = {}

    for name in interp_names:
        interpleveldefs[name] = 'interp_operator.%s' % name

    mapping = {
    '__abs__' : 'abs',
    '__add__' : 'add',
    '__and__' : 'and_',
    '__concat__' : 'concat',
    '__contains__' : 'contains',
    'sequenceIncludes' : 'contains',
    '__delitem__' : 'delitem',
    '__div__' : 'div',
    '__eq__' : 'eq',
    '__floordiv__' : 'floordiv',
    '__ge__' : 'ge',
    '__getitem__' : 'getitem',
    '__gt__' : 'gt',
    '__inv__' : 'inv',
    '__invert__' : 'invert',
    '__le__' : 'le',
    '__lshift__' : 'lshift',
    '__lt__' : 'lt',
    '__mod__' : 'mod',
    '__mul__' : 'mul',
    '__ne__' : 'ne',
    '__neg__' : 'neg',
    '__not__' : 'not_',
    '__or__' : 'or_',
    '__pos__' : 'pos',
    '__pow__' : 'pow',
    '__rshift__' : 'rshift',
    '__setitem__' : 'setitem',
    '__sub__' : 'sub',
    '__truediv__' : 'truediv',
    '__xor__' : 'xor',
    }
