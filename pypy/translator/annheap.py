from __future__ import generators
import types
from annotation import Annotation, XCell, XConstant, nothingyet


class AnnotationHeap:
    """An annotation heap is a (large) family of Annotations."""

    # XXX STORED AS A PLAIN LIST, THE COMPLEXITY IS PLAINLY WRONG

    def __init__(self, annlist=[]):
        self.annlist = list(annlist)    # List of annotations

    def dump(self):     # debugging
        for ann in self.enumerate():
            print ann

    def enumerate(self):
        """Enumerates all annotations in the heap."""
        return iter(self.annlist)

    __iter__ = enumerate

    def simplify(self, kill=[]):
        """Kill annotations in the list, and recursively all the annotations
        that depend on them, and simplify the resulting heap to remove
        duplicates."""
        # temporarykey() returns a tuple with all the information about
        # the annotation; equal temporarykey() means equal annotations.
        # Such keys are temporary because making new XCells shared can
        # change the temporarykey(), but this doesn't occur during
        # one call to simplify().
        
        allkeys = {}   # map temporarykeys to Annotation instances
        for ann in self.annlist:
            key = ann.temporarykey()
            if key in allkeys:  # duplicate?
                previous = allkeys[key]
                previous.forward_deps += ann.forward_deps   # merge
            else:
                allkeys[key] = ann

        killkeys = {}  # set of temporarykeys of annotations to remove
        for ann in kill:
            killkeys[ann.temporarykey()] = True

        pending = killkeys.keys()
        for key in pending:
            if key in allkeys:
                ann = allkeys[key]
                del allkeys[key]    # remove annotations from the dict
                for dep in ann.forward_deps:   # propagate dependencies
                    depkey = dep.temporarykey()
                    if depkey not in killkeys:
                        killkeys[depkey] = True
                        pending.append(depkey)

        self.annlist = allkeys.values()

    def merge(self, oldcell, newcell):
        """Update the heap to account for the merging of oldcell and newcell.
        Return the merged cell."""
        if newcell is nothingyet or newcell == oldcell:
            return oldcell
        elif oldcell is nothingyet:
            return newcell
        else:
            # any annotation or "constantness" about oldcell that must be killed?
            deleting = isinstance(oldcell, XConstant)
            # find the annotations common to oldcell and newcell
            common = []
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
            if Annotation('immutable', [], newcell) in common:
                # for immutable objects we can create a new cell if necessary
                if not deleting:
                    return oldcell  # nothing must be removed from oldcell
                else:
                    resultcell = XCell()  # invent a new cell
                    for ann in common:
                        self.annlist.append(rename(ann, newcell, resultcell))
                    return resultcell
            else:
                if Annotation('immutable', [], oldcell) in self.annlist:
                    pass # old was immutable, don't touch it
                elif Annotation('immutable', [], newcell) in self.annlist:
                    # new is immutable, old was not, inverse the roles
                    oldcell, newcell = newcell, oldcell
                else:
                    # two mutable objects: we identify oldcell and newcell
                    newcell.share(oldcell)
                # only keep the common annotations by listing all annotations
                # to remove, which are the ones that talk about newcell but
                # are not in 'common'.
                deleting = []
                for ann in self.annlist:
                    if newcell in ann.args or newcell == ann.result:
                        if ann not in common:
                            deleting.append(ann)
                # apply changes
                self.simplify(kill=deleting)
                return newcell


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
    return Annotation(ann.opname, args, a)


class Transaction:
    """A transaction contains methods to look for annotations in the
    AnnotationHeap and create new annotations accordingly.  Each
    Transaction instance records which Annotations were needed, which
    allows dependencies to be tracked."""

    def __init__(self, heap):
        self.heap = heap
        self.using_annotations = []  # annotations that we have used

    def get(self, opname, args):
        """Return the Cell with the annotation 'opname(args) -> Cell',
        or None if there is no such annotation or several different ones."""
        matchann = None
        for ann in self.heap.annlist:
            if ann.opname == opname and ann.args == args:
                if matchann is None:
                    matchann = ann     # first possible annotation
                elif matchann != ann:
                    return None        # more than one annotation would match
        if matchann is None:
            return None
        else:
            self.using(matchann)
            return matchann.result
        # a note about duplicate Annotations in annlist: their forward_deps
        # lists will automatically be merged during the next simplify(),
        # so that we only need to record the dependency from one of them.

    def set(self, opname, args, result):
        """Put a new annotation into the AnnotationHeap."""
        ann = Annotation(opname, args, result)
        for prev in self.using_annotations:
            prev.forward_deps.append(ann)
        self.heap.annlist.append(ann)

    def get_type(self, cell):
        """Get the type of 'cell', as specified by the annotations, or None."""
        # Returns None if cell is None.
        assert isinstance(cell, XCell) or cell is None
        c = self.get('type', [cell])
        if isinstance(c, XConstant):
            return c.value
        else:
            return None

    def set_type(self, cell, type):
        """Register an annotation describing the type of the object 'cell'."""
        self.set('type', [cell], XConstant(type))
        if type in immutable_types:
            self.set('immutable', [], cell)

    def using(self, ann):
        """Mark 'ann' as used in this transaction."""
        self.using_annotations.append(ann)


immutable_types = {
    int: True,
    long: True,
    tuple: True,
    str: True,
    bool: True,
    types.FunctionType: True,
    }
