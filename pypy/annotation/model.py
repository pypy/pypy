import types

class SomeValue:
    pass

class QueryArgument:
    pass

class Predicate:
    def __init__(self, debugname, arity):
        self.debugname = debugname
        self.arity = arity
    def __getitem__(self, args):
        if self.arity == 1:
            args = (args,)
        return Annotation(self, *args)
    def __str__(self):
        return self.debugname

class ConstPredicate(Predicate):
    def __init__(self, value):
        Predicate.__init__(self, 'const%s' % value, 1)
        self.value = value
    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.value == other.value
    def __ne__(self, other):
        return not (self == other)
    def __hash__(self):
        return hash(self.value)

class ANN:
    add = Predicate('add', 3)
    constant = ConstPredicate
    type = Predicate('type', 2)
    immutable = Predicate('immutable', 1)

class Annotation:
    """An Annotation asserts something about SomeValues.  
       It is a Predicate applied to some arguments. """
    
    def __init__(self, predicate, *args):
        self.predicate = predicate      # the operation or predicate
        self.args      = list(args)     # list of SomeValues
        assert len(args) == predicate.arity
        # note that for predicates that are simple operations like
        # op.add, the result is stored as the last argument.
        for someval in args:
            assert isinstance(someval, (SomeValue, QueryArgument,
                                        type(Ellipsis)))     # bug catcher

    def copy(self, renameargs={}):
        args = [renameargs.get(arg, arg) for arg in self.args]
        return Annotation(self.predicate, *args)

    def __repr__(self):
        return "Annotation(%s, %s)" % (
                self.predicate, ", ".join(map(debugname, self.args)))

def debugname(someval, _seen = {}):
    """ return a simple name for a SomeValue. """
    try:
        return _seen[id(someval)]
    except KeyError:
        if not _seen:
            for name, value in globals().items():
                if isinstance(value, SomeValue):
                    _seen[id(value)] = name
            return debugname(someval)
        name = "V%d" % len(_seen)
        _seen[id(someval)] = name
        return name

immutable_types = {
    int: 'int',
    long: 'long',
    tuple: 'tuple',
    str: 'str',
    bool: 'bool',
    types.FunctionType: 'function',
    }

# a conventional value for representing 'all Annotations match this one' 
blackholevalue = Ellipsis

# a few values representing 'any value of the given type'
# the following loops creates intvalue, strvalue, etc.
basicannotations = []
for _type, _name in immutable_types.items():
    _val = globals()['%svalue' % _name] = SomeValue()
    _tval = SomeValue()
    basicannotations.append(ANN.type[_val, _tval])
    basicannotations.append(ANN.constant(_type)[_tval])
    basicannotations.append(ANN.immutable[_val])
