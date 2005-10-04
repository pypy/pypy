from pypy.interpreter.astcompiler import ast

def flatten(tup):
    elts = []
    for elt in tup:
        if type(elt) == tuple:
            elts = elts + flatten(elt)
        else:
            elts.append(elt)
    return elts

class Counter:
    def __init__(self, initial):
        self.count = initial

    def next(self):
        i = self.count
        self.count += 1
        return i

MANGLE_LEN = 256 # magic constant from compile.c

def mangle(name, klass):
    if not name.startswith('__'):
        return name
    if len(name) + 2 >= MANGLE_LEN:
        return name
    if name.endswith('__'):
        return name
    try:
        i = 0
        while klass[i] == '_':
            i = i + 1
    except IndexError:
        return name
    klass = klass[i:]

    tlen = len(klass) + len(name)
    if tlen > MANGLE_LEN:
        end = len(klass) + MANGLE_LEN-tlen
        if end < 0:
            klass = ''     # annotator hint
        else:
            klass = klass[:end]

    return "_%s%s" % (klass, name)

def set_filename(filename, tree):
    """Set the filename attribute to filename on every node in tree"""
    worklist = [tree]
    while worklist:
        node = worklist.pop(0)
        assert isinstance(node, ast.Node)
        node.filename = filename
        worklist.extend(node.getChildNodes())
