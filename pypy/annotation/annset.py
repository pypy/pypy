from __future__ import generators
import types
from model import Annotation, SomeValue, QueryArgument, ANN, ConstPredicate
from model import immutable_types, blackholevalue, basicannotations

QUERYARG = QueryArgument()


class AnnotationSet:
    """An annotation set is a (large) family of Annotations."""

    # XXX STORED AS A PLAIN LIST, THE COMPLEXITY IS PLAINLY WRONG

    def __init__(self, annlist=basicannotations):  
        self.annlist = list(annlist)    # List of annotations
        self._normalized = {}  # maps SomeValues to some 'standard' one that
                               # is shared with it
        self.mappings_to_normalize = [self._normalized]

    def getbindings(self):
        """Return a general-purpose mapping between whatever you want and
        SomeValues.  The SomeValues are kept normalized by the AnnotationSet."""
        bindings = {}
        self.mappings_to_normalize.append(bindings)
        return bindings

    def normalized(self, someval):
        return self._normalized.get(someval, someval)

    def setshared(self, someval1, someval2):
        someval1 = self.normalized(someval1)
        someval2 = self.normalized(someval2)
        for mapping in self.mappings_to_normalize:
            for key, value in mapping.items():
                if value is someval2:
                    mapping[key] = someval1
        self._normalized[someval2] = someval1
    
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

    def findall(self, checkann):
        """ list all matching annotations."""
        return list(self._annmatches(checkann))

    def queryconstant(self, cell):
        "Return the list of all 'x' such that ANN.constant(x)[cell] is set."
        cell = self.normalized(cell)
        result = []
        for ann in self.annlist:
            if isinstance(ann.predicate, ConstPredicate) and ann.args[0] is cell:
                result.append(ann.predicate.value)
        return result

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
        """Kill annotations in the 'kill' list, and normalize and remove
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
            if key not in allkeys:  # if not duplicate
                allkeys[key] = ann

        for ann in kill:
            key = temporarykey(ann)
            if key in allkeys:
                del allkeys[key]

        self.annlist = allkeys.values()

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
                return resultcell

    def get(self, *querylist):
        """Like query() but asserts that there is at most one answer.
        Returns None if there isn't any answer."""
        resultlist = self.query(*querylist)
        assert len(resultlist) <= 1, "Confusing annotations..."
        if resultlist:
            return resultlist[0]
        else:
            return None

    def set(self, ann):
        """Insert the annotation into the AnnotationSet."""
        self.normalizeann(ann)
        self.annlist.append(ann)

    def delete(self, queryann):
        """Kill the annotations matching the pattern."""
        matchannlist = self.findall(queryann)
        self.simplify(kill=matchannlist)

    def checktype(self, someval, checktype):
        if isinstance(checktype, tuple):
            for t in checktype:
                if self.checktype(someval, t):
                    return True
            else:
                return False
        else:
            return bool(self.query(ANN.type[someval, QUERYARG],
                                   ANN.constant(checktype)[QUERYARG]))

    def settype(self, someval, knowntype):
        typeval = SomeValue()
        self.set(ANN.type[someval, typeval])
        self.set(ANN.constant(knowntype)[typeval])
        if knowntype in immutable_types:
            self.set(ANN.immutable[someval])

    def newconstant(self, value):
        cell = SomeValue()
        self.set(ANN.constant(value)[cell])
        return cell

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
