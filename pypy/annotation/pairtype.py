"""
XXX A docstring should go here.
"""

class extendabletype(type):
    """A type with a syntax trick: 'class __extend__(t)' actually extends
    the definition of 't' instead of creating a new subclass."""
    def __new__(cls, name, bases, dict):
        if name == '__extend__':
            cls = bases[0]   # override data into the existing base
            for key, value in dict.items():
                setattr(cls, key, value)
            return None
        else:
            return super(extendabletype, cls).__new__(cls, name, bases, dict)


def pair(a, b):
    """Return a pair object."""
    tp = pairtype(a.__class__, b.__class__)
    return tp((a, b))   # tp is a subclass of tuple

pairtypecache = {}

def pairtype(cls1, cls2):
    """type(pair(a,b)) is pairtype(a.__class__, b.__class__)."""
    try:
        pair = pairtypecache[cls1, cls2]
    except KeyError:
        name = 'pairtype(%s, %s)' % (cls1.__name__, cls2.__name__)
        bases1 = [pairtype(base1, cls2) for base1 in cls1.__bases__]
        bases2 = [pairtype(cls1, base2) for base2 in cls2.__bases__]
        bases = tuple(bases1 + bases2) or (tuple,)  # 'tuple': ultimate base
        pair = pairtypecache[cls1, cls2] = extendabletype(name, bases, {})
    return pair


# ____________________________________________________________

if __name__ == '__main__':
    from unittest2 import check
    
    ### Binary operation example
    class __extend__(pairtype(int, int)):
        def add((x, y)):
            return 'integer: %s+%s' % (x, y)
        def sub((x, y)):
            return 'integer: %s-%s' % (x, y)

    class __extend__(pairtype(bool, bool)):
        def add((x, y)):
            return 'bool: %s+%s' % (x, y)

    check.equal(pair(3,4).add(), 'integer: 3+4')
    check.equal(pair(3,4).sub(), 'integer: 3-4')
    check.equal(pair(3,True).add(), 'integer: 3+True')
    check.equal(pair(3,True).sub(), 'integer: 3-True')
    check.equal(pair(False,4).add(), 'integer: False+4')
    check.equal(pair(False,4).sub(), 'integer: False-4')
    check.equal(pair(False,True).add(), 'bool: False+True')
    check.equal(pair(False,True).sub(), 'integer: False-True')

    ### Operation on built-in types
    class MiniPickler:
        def __init__(self):
            self.data = []
        def emit(self, datum):
            self.data.append(datum)

    class __extend__(pairtype(MiniPickler, int)):
        def write((pickler, x)):
            pickler.emit('I%d' % x)

    class __extend__(pairtype(MiniPickler, str)):
        def write((pickler, x)):
            pickler.emit('S%s' % x)

    class __extend__(pairtype(MiniPickler, list)):
        def write((pickler, x)):
            for item in x:
                pair(pickler, item).write()
            pickler.emit('L%d' % len(x))

    p = MiniPickler()
    pair(p, [1, 2, ['hello', 3]]).write()
    check.equal(p.data, ['I1', 'I2', 'Shello', 'I3', 'L2', 'L3'])

    ### Another multimethod example
    class Block:
        def __init__(self, exit):
            self.exit = exit
    class Jump:
        pass
    class Switch:
        pass
    
    class C_Generator:
        def __init__(self):
            self.lines = []

    class __extend__(pairtype(C_Generator, Block)):
        def emit((gen, block), inputvars):
            gen.lines.append("C code for block")
            outputvars = inputvars + ['v4', 'v5']
            pair(gen, block.exit).emit(outputvars)

    class __extend__(pairtype(C_Generator, Jump)):
        def emit((gen, jump), inputvars):
            gen.lines.append("goto xyz")

    class __extend__(pairtype(C_Generator, Switch)):
        def emit((gen, jump), inputvars):
            gen.lines.append("switch (%s) { ... }" % inputvars[-1])

    g = C_Generator()
    pair(g, Block(Switch())).emit(['v1', 'v2'])
    check.equal(g.lines, ["C code for block",
                          "switch (v5) { ... }"])

    class Lisp_Generator:
        def __init__(self):
            self.progn = []

    class __extend__(pairtype(Lisp_Generator, Block)):
        def emit((gen, block), inputvars):
            gen.progn.append("(do 'something)")

    g = Lisp_Generator()
    pair(g, Block(Switch())).emit(['v1', 'v2'])
    check.equal(g.progn, ["(do 'something)"])
