import types

class SomeValue:
    def __repr__(self):
        return debugname(self, 'SV')

class Predicate:
    def __init__(self, debugname):
        self.debugname = debugname
    def __str__(self):
        return self.debugname

class PredicateFamily:
    def __init__(self, familyname):
        self.familyname = familyname
        self.instances = {}
    def __getitem__(self, index):
        try:
            return self.instances[index]
        except KeyError:
            name = '%s[%r]' % (self.familyname, index)
            pred = self.instances[index] = Predicate(name)
            return pred

class ANN:
    len       = Predicate('len')
    listitems = Predicate('listitems')
    tupleitem = PredicateFamily('tupleitem')
    const     = Predicate('const')
    type      = Predicate('type')
    immutable = Predicate('immutable')


def debugname(someval, prefix, _seen = {}):
    """ return a simple name for a SomeValue. """
    try:
        return _seen[id(someval)]
    except KeyError:
        name = "%s%d" % (prefix, len(_seen))
        _seen[id(someval)] = name
        return name

immutable_types = {
    int: 'int',
    long: 'long',
    tuple: 'tuple',
    str: 'str',
    bool: 'bool',
    slice: 'slice',
    types.FunctionType: 'function',
    }
