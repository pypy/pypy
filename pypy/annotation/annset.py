from __future__ import generators
import types
from model import Annotation, SomeValue, blackholevalue

class AnnotationSet:
    """An annotation set is a (large) family of Annotations."""

    # XXX STORED AS A PLAIN LIST, THE COMPLEXITY IS PLAINLY WRONG

    def __init__(self, annlist=[]):
        self.annlist = list(annlist)    # List of annotations
        self._shared = {}

    def getsharelist(self, someval):
        return self._shared.get(someval, [someval])

    def setshared(self, someval1, someval2):
        list1 = self.getsharelist(someval1)
        list2 = self.getsharelist(someval2)
        newlist = list1 + list2
        for someval in newlist:
            self._shared[someval] = newlist
    
    def isshared(self, someval1, someval2):
        return (self._shared.get(someval1, someval1) is
                self._shared.get(someval2, someval2))

    def tempid(self, someval):
        return id(self.getsharelist(someval)[0])

    def dump(self):     # debugging
        for ann in self.enumerate():
            print ann

    def enumerate(self):
        """Enumerates all annotations in the heap."""
        return iter(self.annlist)

    __iter__ = enumerate

    def query(self, *querylist):
        return [match for depends, match in self.getmatches(*querylist)]

    def getmatches(self, query, *querylist):
        # slightly limited implementation for ease of coding :-)
        assert query.args.count(Ellipsis) == 1, (
            "sorry, the algorithm is a bit too naive for this case")
        queryarg = query.args.index(Ellipsis)
        for ann in self._annmatch(query):
            # does the returned match also agree with the other queries?
            match = ann.args[queryarg]
            depends = [ann]
            for queryann in querylist:
                boundquery = queryann.copy(renameargs={Ellipsis: match})
                ann = self.findfirst(boundquery)
                if ann is None:
                    break
                depends.append(ann)
            else:
                yield depends, match

    def _annmatch(self, queryann):
        testindices = [i for i in range(queryann.predicate.arity)
                         if queryann.args[i] is not Ellipsis]
        for ann in self.annlist:
            if ann.predicate == queryann.predicate:
                for i in testindices:
                    if not self.isshared(ann.args[i], queryann.args[i]):
                        break
                else:
                    yield ann

    def findfirst(self, checkann):
        """ return the first matching annotation.""" 
        # note that we are usually not interested in multiple matching 
        # annotations; e.g. killing an annotation will take care
        # that all matching annotations are removed, and thus also 
        # all dependencies listed on any of the duplicate annotation.
        for ann in self._annmatch(checkann):
            return ann  # :-)
        else:
            return None


class Recorder:
    """A recorder contains methods to look for annotations in the
    AnnotationSet and create new annotations accordingly.  Each
    Recorder instance records which Annotations were needed, which
    allows dependencies to be tracked."""

    def __init__(self, annset):
        self.annset = annset
        self.using_annotations = []  # annotations that we have used

    def using(self, *annlist):
        """Mark all 'ann' in 'annlist' as used in this transaction."""
        self.using_annotations += annlist

    def query(self, *querylist):
        results = []
        for depends, match in self.annset.getmatches(*querylist):                
            self.using(*depends)
            results.append(match)
        return results

'''
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
'''


class XXXTransaction:
    """A transaction contains methods to look for annotations in the
    AnnotationHeap and create new annotations accordingly.  Each
    Transaction instance records which Annotations were needed, which
    allows dependencies to be tracked."""

    def __init__(self, heap):
        self.heap = heap
        self.using_annotations = []  # annotations that we have used

    def _list_annotations(self, opname, args):
        # patch(arglist) -> arglist with None plugged where
        #                   there is a None in the input 'args'
        def patch(arglist):
            return arglist
        for i in range(len(args)):
            if args[i] is None:
                def patch(arglist, prevpatch=patch, i=i):
                    arglist = prevpatch(arglist)[:]
                    arglist[i] = None
                    return arglist
        
        matchann = []
        for ann in self.heap.annlist:
            if ann.opname == opname and patch(ann.args) == args:
                matchann.append(ann)
        return matchann

    def get(self, opname, args):
        """Return the Cell with the annotation 'opname(args) -> Cell',
        or None if there is no such annotation or several different ones.
        Hack to generalize: a None in the args matches anything."""
        matchann = self._list_annotations(opname, args)
        if not matchann:
            return None
        else:
            result = matchann[0].result
            for ann in matchann[1:]:
                if result != ann.result:
                    return None   # conflicting results
            for ann in matchann:
                self.using(ann)
            return result

    def delete(self, opname, args):
        """Kill the annotations 'opname(args) -> *'."""
        matchann = self._list_annotations(opname, args)
        self.heap.simplify(kill=matchann)

    def set(self, opname, args, result):
        """Put a new annotation into the AnnotationHeap."""
        ann = Annotation(opname, args, result)
        for prev in self.using_annotations:
            prev.forward_deps.append(ann)
        self.heap.annlist.append(ann)

    def get_type(self, cell):
        """Get the type of 'cell', as specified by the annotations, or None.
        Returns None if cell is None."""
        if cell is None:
            return None
        assert isinstance(cell, XCell)
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
