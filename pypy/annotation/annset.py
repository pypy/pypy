from __future__ import generators
import types
from model import Annotation, SomeValue, QueryArgument, ANN
from model import immutable_types, blackholevalue, basicannotations

QUERYARG = QueryArgument()


class AnnotationSet:
    """An annotation set is a (large) family of Annotations."""

    # XXX STORED AS A PLAIN LIST, THE COMPLEXITY IS PLAINLY WRONG

    def __init__(self, annlist=basicannotations):  
        self.annlist = list(annlist)    # List of annotations
        self._shared = {}
        self.forward_deps = {}

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

    def annequal(self, ann1, ann2):
        if ann1.predicate != ann2.predicate:
            return False
        for a1, a2 in zip(ann1.args, ann2.args):
            if not self.isshared(a1, a2):
                return False
        return True

    def temporarykey(self, ann):
        """ a temporary hashable representation of an annotation """
        return (ann.predicate, tuple([self.tempid(arg) for arg in ann.args]))

    def dump(self):     # debugging
        for ann in self.enumerate():
            print ann

    def enumerate(self):
        """Enumerates all annotations in the heap."""
        return iter(self.annlist)

    __iter__ = enumerate

    def query(self, *querylist):
        return [matchvalue for matchanns, matchvalue in self.match(*querylist)]

    def match(self, query, *querylist):
        """ yield (matchanns, matchvalue) tuples with 'matchanns'
        beeing a list of matching annotations and 'matchvalue' beeing
        the queried value. """

        # slightly limited implementation for ease of coding :-)
        assert query.args.count(QUERYARG) == 1, (
            "sorry, the algorithm is a bit too naive for this case")
        queryarg = query.args.index(QUERYARG)
        for ann in self._annmatches(query):
            # does the returned match also agree with the other queries?
            match = ann.args[queryarg]
            depends = [ann]
            for queryann in querylist:
                boundquery = queryann.copy(renameargs={QUERYARG: match})
                ann = self.findfirst(boundquery)
                if ann is None:
                    break
                depends.append(ann)
            else:
                yield depends, match

    def _annmatches(self, queryann):
        """ yield annotations matching the given queryannotation. """
        testindices = [i for i in range(queryann.predicate.arity)
                             if queryann.args[i] is not QUERYARG]
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
        for ann in self._annmatches(checkann):
            return ann  # :-)
        else:
            return None

    def record(self, recfunc, *args):
        """ invoke the given 'recording' function by passing it a new 
        Recorder instance and letting it use its modification API.  This API will
        make sure that for the typical read/decide/write usage the read 
        annotations are a perequisite of the later write/modification 
        operation. Thus if the "causing" annotation gets invalidated we
        know which "depending" annotations need to be removed. """
        rec = Recorder(self)
        return recfunc(rec, *args)

    def kill(self, *annlist):
        self.simplify(kill=annlist)

    def simplify(self, kill=[]):
        """Kill annotations in the list, and recursively all the annotations
        that depend on them, and simplify the resulting list to remove
        duplicates."""
        # temporarykey() returns a tuple with all the information about
        # the annotation; equal temporarykey() means equal annotations.
        # Such keys are temporary because making SomeValues shared can
        # change the temporarykey(), but this doesn't occur during
        # one call to simplify().
        
        allkeys = {}   # map temporarykeys to Annotation instances
        for ann in self.annlist:
            key = self.temporarykey(ann)
            if key in allkeys:  # duplicate?
                previous = allkeys[key]
                if ann in self.forward_deps:
                    deps = self.forward_deps.setdefault(previous, [])
                    deps += self.forward_deps[ann]   # merge
            else:
                allkeys[key] = ann

        killkeys = {}  # set of temporarykeys of annotations to remove
        for ann in kill:
            killkeys[self.temporarykey(ann)] = True
        
        pending = killkeys.keys()
        for key in pending:
            if key in allkeys:
                ann = allkeys[key]
                del allkeys[key]    # remove annotations from the dict
                if ann in self.forward_deps:
                    for dep in self.forward_deps[ann]:   # propagate dependencies
                        depkey = self.temporarykey(dep)
                        if depkey not in killkeys:
                            killkeys[depkey] = True
                            pending.append(depkey)
                    del self.forward_deps[ann]

        self.annlist = allkeys.values()


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
        for matchanns, matchvalue in self.annset.match(*querylist):                
            self.using(*matchanns)
            results.append(matchvalue)
        return results

    def set(self, ann):
        """Insert the annotation into the AnnotationSet, recording dependency
        from all previous queries done on this Recorder instance."""
        self.annset.annlist.append(ann)
        for previous_ann in self.using_annotations:
            deps = self.annset.forward_deps.setdefault(previous_ann, [])
            deps.append(ann)

    def check_type(self, someval, checktype):
        return bool(self.query(ANN.type[someval, QUERYARG],
                               ANN.constant(checktype)[QUERYARG]))

    def set_type(self, someval, knowntype):
        typeval = SomeValue()
        self.set(ANN.type[someval, typeval])
        self.set(ANN.constant(knowntype)[typeval])
        if knowntype in immutable_types:
            self.set(ANN.immutable[someval])

'''
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

if __name__ == '__main__':
    val1, val2, val3 = SomeValue(), SomeValue(), SomeValue()
    annset = AnnotationSet()

