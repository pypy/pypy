import weakref


class Annotation:
    """An Annotation asserts something about heap objects represented
    by XCell instances."""
    
    # Note that this is very much like a SpaceOperation, but we keep
    # them separate because they have different purposes.

    # Attention, handle Annotations with care!  Two Annotations that
    # were initially different could become equal when XCells become
    # shared.  This is the reason why Annotations are not hashable.

    def __init__(self, opname, args, result):
        self.opname = opname      # operation name
        self.args   = list(args)  # list of XCells
        self.result = result      # an XCell
        self.forward_deps = []    # annotations that depend on this one
        # catch bugs involving confusion between Variables/Constants
        # and XCells/XConstants
        for cell in args + [result]:
            assert isinstance(cell, XCell)

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and 
                self.opname == other.opname and
                self.args == other.args and
                self.result == other.result)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "%s(%s) -> %s" % (self.opname, ", ".join(map(repr, self.args)),
                                 self.result)

    def temporarykey(self):
        lst = [self.opname, self.result.temporarykey()]
        lst += [arg.temporarykey() for arg in self.args]
        return tuple(lst)


class XCell:
    """A placeholder for a heap object contained in an AnnotationHeap.
    It represents an object that will actually appear at run-time in the heap.
    XCells are the arguments and return value of Annotations."""

    counter = 0

    # Multiple XCells can be "shared"; a group of shared cells
    # act essentially like a single cell (they become all equal).
    
    def __init__(self, name=None):
        if not name:
            name = 'X%d' % XCell.counter
            XCell.counter += 1
        self.name = name
        self.shared = []    # list of weakrefs to XCells
                            # defining a group of shared cells.

    def __repr__(self):
        names = [cell.name for cell in self.cellsingroup()]
        names.sort()
        return '=='.join(names)

    def __eq__(self, other):
        "Two sharing cells are equal."
        return isinstance(other, XCell) and self.is_shared(other)

    def __ne__(self, other):
        return not (self == other)

    def temporarykey(self):
        ids = [id(cell) for cell in self.cellsingroup()]
        return min(ids)

    def cellsingroup(self):
        if self.shared:
            l = [s() for s in self.shared]
            assert self in l
            return [c for c in l if c is not None]
        else:
            return [self]

    def getsharelist(self):
        if not self.shared:
            self.shared = [weakref.ref(self)]
        return self.shared

    def is_shared(self, other):
        "Test if two cells are shared."
        return self.shared is other.shared

    def share(self, other):
        "Make two cells shared."
        if not self.is_shared(other):
            lst1 = self.getsharelist()
            lst2 = other.getsharelist()
            for s in lst2:
                c = s()
                if c is not None:
                    c.shared = lst1
                    lst1.append(s)


class XConstant(XCell):
    """A fully determined XCell.  For immutable constants."""

    def __init__(self, value):
        XCell.__init__(self)
        self.value = value

    def __eq__(self, other):
        "Two constants with the same value are equal."
        return (isinstance(other, XConstant) and self.value == other.value
                or XCell.__eq__(self, other))

    def __repr__(self):
        if self.shared:
            return 'UNEXPECTEDLY SHARED %r' % XCell.__repr__(self)
        else:
            return 'XConstant %r' % self.value


# The more annotations about an XCell, the least general
# it is.  Extreme case: *all* possible annotations stand for an
# object that cannot exist (e.g. the return value of a function
# that never returns or we didn't see return so far).
# This is specified by using nothingyet instead of a real XCell().
# Conversely, *no* annotation stands for any object.

nothingyet = XCell('nothingyet')
