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
        self._normalized = {}  # maps SomeValues to some 'standard' one that
                               # is shared with it

    def normalized(self, someval):
        return self._normalized.get(someval, someval)

    def setshared(self, someval1, someval2):
        someval1 = self.normalized(someval1)
        someval2 = self.normalized(someval2)
        for key, value in self._normalized.items():
            if value is someval1:
                self._normalized[key] = someval2
        self._normalized[someval1] = someval2
    
    def isshared(self, someval1, someval2):
        return self.normalized(someval1) is self.normalized(someval2)

    def normalizeann(self, ann):
        "Normalize the annotation's arguments in-place."
        ann.args = [self.normalized(a) for a in ann.args]

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
        self.normalizeann(query)
        for queryann in querylist:
            self.normalizeann(queryann)

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
        self.normalizeann(queryann)
        testindices = [i for i in range(queryann.predicate.arity)
                             if isinstance(queryann.args[i], SomeValue)]
        for ann in self.annlist:
            if ann.predicate == queryann.predicate:
                for i in testindices:
                    if ann.args[i] is not queryann.args[i]:
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

        def temporarykey(ann):
            self.normalizeann(ann)
            return ann.predicate, tuple(ann.args)
        
        allkeys = {}   # map temporarykeys to Annotation instances
        for ann in self.annlist:
            key = temporarykey(ann)
            if key in allkeys:  # duplicate?
                previous = allkeys[key]
                previous.forward_deps += ann.forward_deps  # merge
            else:
                allkeys[key] = ann

        killkeys = {}  # set of temporarykeys of annotations to remove
        for ann in kill:
            killkeys[temporarykey(ann)] = True
        
        pending = killkeys.keys()
        for key in pending:
            if key in allkeys:
                ann = allkeys[key]
                del allkeys[key]    # remove annotations from the dict
                for dep in ann.forward_deps:   # propagate dependencies
                    depkey = temporarykey(dep)
                    if depkey not in killkeys:
                        killkeys[depkey] = True
                        pending.append(depkey)

        self.annlist = allkeys.values()

    def adddependency(self, hypothesisann, conclusionann):
        hypothesisann.forward_deps.append(conclusionann)

    def merge(self, oldcell, newcell):
        """Update the heap to account for the merging of oldcell and newcell.
        Return the merged cell."""
        oldcell = self.normalized(oldcell)
        newcell = self.normalized(newcell)
        
        if newcell is blackholevalue or newcell is oldcell:
            return oldcell
        elif oldcell is blackholevalue:
            return newcell

        # if 'oldcell' or 'newcell' is immutable, we should not
        # modify the annotations about it.  If one of them is mutable,
        # then we must update its annotations and return it.  As a
        # consequence if both are mutable then we must return them both,
        # i.e. make them shared.

        mutablecells = []
        deleting = []
        annlist = self.annlist
        for cell, othercell in [(oldcell, newcell), (newcell, oldcell)]:
            if ANN.immutable[cell] not in annlist:
                # for each mutable 'cell', kill the annotation that are
                # talking about 'cell' but not existing for 'othercell'.
                for ann in annlist:
                    if cell in ann.args:
                        otherann = ann.copy(renameargs={cell: othercell})
                        if otherann not in annlist:
                            deleting.append(ann)
                mutablecells.append(cell)

        if mutablecells:
            # if there is at least one mutable cell we must return it.
            # if there are two mutable cells we must merge them.
            if len(mutablecells) == 2:
                self.setshared(oldcell, newcell)
            self.simplify(kill=deleting)
            return self.normalized(mutablecells[0])
        else:
            # no mutable cell, we can create a new result cell
            # with only the common annotations.
            common = []
            deleting = False  # False if annotations of oldcell
                              #         == annotations common annotations
            for ann in annlist:
                if oldcell in ann.args:
                    newann = ann.copy(renameargs={oldcell: newcell})
                    try:
                        i = annlist.index(newann)
                    except ValueError:
                        deleting = True  # this annotation about 'oldcell'
                                         # is no longer there about 'newcell'.
                    else:
                        newann = annlist[i]  # existing Annotation
                        common.append((ann, newann))

            if not deleting:
                return oldcell  # nothing must be removed from oldcell
            else:
                resultcell = SomeValue()  # invent a new cell
                for oldann, newann in common:
                    resultann = newann.copy(renameargs={newcell: resultcell})
                    annlist.append(resultann)
                    self.adddependency(oldann, resultann)
                    self.adddependency(newann, resultann)
                return resultcell


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
        self.annset.normalizeann(ann)
        self.annset.annlist.append(ann)
        for previous_ann in self.using_annotations:
            self.annset.adddependency(previous_ann, ann)

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

'''
