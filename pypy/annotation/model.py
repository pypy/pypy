
class SomeValue:
    pass

# a conventional value for representing 'all Annotations match this one' 
blackholevalue = SomeValue()

def debugname(someval, name=None, _seen = {id(blackholevalue): 'blackholevalue'}):
    """ return a simple name for a SomeValue. """
    try:
        return _seen[id(someval)]
    except KeyError:
        if name is None:
            name = "X%d" % len(seen)
        _seen[id(someval)] = name
        return name

class Predicate:
    def __init__(self, name, arity):
        self.name = name
        self.arity = arity
    def __getitem__(self, args):
        if self.arity == 1:
            args = (args,)
        return Annotation(self, *args)

class ann:
    add = Predicate('add', 3)
    snuff = Predicate('snuff', 2)   # for testing, to remove :-)

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
            assert someval is Ellipsis or isinstance(someval, SomeValue)  # bug catcher

    def copy(self, renameargs={}):
        args = [renameargs.get(arg, arg) for arg in self.args]
        return Annotation(self.predicate, *args)

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and 
                self.predicate == other.predicate and
                self.args == other.args)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "Annotation(%s, %s)" % (
                self.predicate, ", ".join(map(repr, self.args)))


