from __future__ import generators
import weakref
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation


class XCell:
    """A placeholder for a heap object contained in an AnnotationHeap.
    It represents an object that will actually appear at run-time in the heap.
    XCells are the arguments and return value of SpaceOperations when
    used as annotations."""

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


# The more annotations about an XCell, the least general
# it is.  Extreme case: *all* possible annotations stand for an
# object that cannot exist (e.g. the return value of a function
# that never returns or we didn't see return so far).
# This is specified by using nothingyet instead of a real XCell().
# Conversely, *no* annotation stands for any object.

nothingyet = XCell('nothingyet')


class AnnotationHeap:
    """An annotation heap is a (large) family of annotations.
    An annotation is a SpaceOperation with XCells as arguments and result."""

    def __init__(self, annlist=[]):
        self.annlist = []    # List of annotations  XXX optimize
        for ann in annlist:
            self.add(ann)

    def dump(self):     # debugging
        for ann in self.enumerate():
            print ann

    def add(self, annotation):
        """Register an annotation into the heap."""
        if annotation not in self.annlist:
            self.annlist.append(annotation)

    def enumerate(self):
        """Enumerates all annotations in the heap."""
        return iter(self.annlist)

    __iter__ = enumerate

    def set_type(self, cell, type):
        """Register an annotation describing the type of the object 'cell'."""
        self.add(SpaceOperation('type', [cell], XConstant(type)))

    def get_type(self, cell):
        """Get the type of 'cell', as specified by the annotations, or None."""
        c = self.get_opresult('type', [cell])
        if isinstance(c, XConstant):
            return c.value
        else:
            return None

    def get_opresult(self, name, args):
        """Return the Cell with the annotation 'name(args) = cell',
        or None if there is no such annotation, or several different ones."""
        result = None
        for ann in self.annlist:
            if ann.opname == name and ann.args == args:
                if result is None:
                    result = ann.result
                elif ann.result != result:
                    return None
        return result

    def merge(self, oldcell, newcell):
        """Update the heap to account for the merging of oldcell and newcell.
        Return (resultcell, changeflag) where resultcell is the merged cell.
        changeflag is false only if the merged cell is equal to oldcell and
        no annotations about oldcell have been dropped."""
        if newcell is nothingyet or newcell == oldcell:
            return oldcell, False
        elif oldcell is nothingyet:
            return newcell, True
        else:
            # find the annotations common to oldcell and newcell
            common = []
            deleting = False  # means deleting an annotation about oldcell
            for ann in self.annlist:
                if oldcell in ann.args or oldcell == ann.result:
                    test1 = rename(ann, oldcell, newcell)
                    test2 = rename(ann, newcell, oldcell)  # may equal 'ann'
                    if test1 in self.annlist and test2 in self.annlist:
                        common.append(test1)
                    else:
                        deleting = True
            # the involved objects are immutable if we have both
            # 'immutable() -> oldcell' and 'immutable() -> newcell'
            if SpaceOperation('immutable', [], newcell) in common:
                # for immutable objects we can create a new cell if necessary
                if not deleting:
                    return oldcell, False  # nothing must be removed from oldcell
                else:
                    resultcell = XCell()  # invent a new cell
                    for ann in common:
                        self.add(rename(ann, newcell, resultcell))
                    return resultcell, True
            else:
                # for mutable objects we must identify oldcell and newcell,
                # and only keep the common annotations
                newcell.share(oldcell)
                # add to 'common' all annotations that don't talk about oldcell
                # (nor newcell, but at this point oldcell == newcell)
                for ann in self.annlist:
                    if not (oldcell in ann.args or oldcell == ann.result):
                        common.append(ann)
                # 'common' is now the list of remaining annotations
                self.annlist[:] = common
                return oldcell, deleting


def rename(ann, oldcell, newcell):
    "Make a copy of 'ann' in which 'oldcell' has been replaced by 'newcell'."
    args = []
    for a in ann.args:
        if a == oldcell:
            a = newcell
        args.append(a)
    a = ann.result
    if a == oldcell:
        a = newcell
    return SpaceOperation(ann.opname, args, a)
