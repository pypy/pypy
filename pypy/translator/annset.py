from __future__ import generators
import weakref
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation


class Cell:
    """A logical variable. A Cell is an initially empty place that can
    later contain a Variable or a Constant."""

    # a Cell is "empty" if self.content is None,
    # a Cell is "ground" otherwise.  Once a Cell is ground its content
    # cannot be changed any more.

    # Multiple empty Cells can be "shared"; a group of shared Cells act
    # essentially like a single Cell in that setting one Cell content
    # will give all Cells in the group the same content.
    
    def __init__(self):
        self.content = None
        self.shared = []    # list of weakrefs to Cells
                            # defining a group of shared cells

    def __repr__(self):
        if self.content is None:
            first = self.cellsingroup()[0]
            return '<Cell G%x>' % (id(first),)
        else:
            return '<Cell(%r)>' % (self.content,)

    def __eq__(self, other):
        "Two sharing cells are identical."
        if isinstance(other, Cell):
            return self.is_shared(other)
        else:
            return self.content == other

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

    def set(self, content):
        if isinstance(content, Cell):
            self.share(content)
        elif self.content is None:
            for c in self.cellsingroup():
                c.content = content
        elif self.content != content:
            raise ValueError, "cannot change the content of %r" % self

    def is_shared(self, other):
        "Test if two cells are shared."
        return self.shared is other.shared

    def share(self, other):
        "Make two Cells share content."
        if not self.is_shared(other):
            if self.content is not None:
                other.set(self.content)
            elif other.content is not None:
                self.set(other.content)
            lst1 = self.getsharelist()
            lst2 = other.getsharelist()
            for s in lst2:
                c = s()
                if c is not None:
                    c.shared = lst1
                    lst1.append(s)


class AnnotationSet:
    
    def __init__(self, annlist=[]):
        self.byfunctor = {}
        for ann in annlist:
            self.add(ann)

    def copy(self):
        a = AnnotationSet()
        for functor, lst in self.byfunctor.items():
            a.byfunctor[functor] = lst[:]
        return a

    def __repr__(self):
        fulllist = list(self.enumerate())
        if fulllist:
            lines = (['<AnnotationSet at 0x%x:' % (id(self),)] +
                     ['  %r' % line for line in fulllist] +
                     ['>'])
        else:
            lines = ['<empty AnnotationSet at 0x%x>' % (id(self),)]
        return '\n'.join(lines)

    def __len__(self):
        result = 0
        for lst in self.byfunctor.values():
            result += len(lst)
        return result

    def match(self, pattern):
        """Test if the annotation 'pattern' is present in the set.
        This function sets all empty Cells of 'pattern', but it does not
        change Cells in 'self'. All Cells of 'pattern' must be fresh."""
        functor = pattern.opname, len(pattern.args)
        for ann in self.byfunctor.get(functor, []):
            if same_functor_assign(pattern, ann):
                return True
        return False

    def intersect(self, otherset):
        """Kill annotations in 'self' that are not present in 'otherset'.
        It may set some Cells in 'self', but it does not change 'otherset'."""
        for annlist in self.byfunctor.values():
            for i in range(len(annlist)-1, -1, -1):
                ann = annlist[i]
                if not otherset.match(ann):
                    del annlist[i]

    def add(self, pattern):
        """Add 'pattern' into 'self'.  It may set some Cells in 'self' instead
        of adding a new entry."""
        functor = pattern.opname, len(pattern.args)
        annlist = self.byfunctor.setdefault(functor, [])
        for ann in annlist:
            if same_functor_assign(ann, pattern):
                pattern = ann
                break
        else:
            annlist.append(pattern)

    def enumerate(self, renaming=None):
        """Yield a copy of all annotations in the set, possibly renaming
        their variables according to a map {Variable: [list-of-Variables]}."""
        if renaming is None:
            def renameall(list_w):
                return [list_w]
        else:
            def rename(w):
                if isinstance(w,Constant):
                    return [w]
                else:
                    return renaming.get(w, [])
            def renameall(list_w):
                if list_w:
                    for w in rename(list_w[0]):
                        for tail_w in renameall(list_w[1:]):
                            yield [w] + tail_w
                else:
                    yield []
        for lst in self.byfunctor.values():
            for ann in lst:
                # we translate a single SpaceOperation(...) into either
                # 0 or 1 or multiple ones, by replacing each variable
                # used in the original operation by (in turn) any of
                # the variables it can be renamed into
                for list_w in renameall([ann.result] + ann.args):
                    result = list_w[0]
                    args = list_w[1:]
                    yield SpaceOperation(ann.opname,args,result)

    __iter__ = enumerate

    ### convenience methods ###

    def set_type(self, v, type):
        self.add(SpaceOperation('type', [v], Constant(type)))

    def get_type(self, v):
        if isinstance(v, Constant):
            return type(v.value)
        c = Cell()
        self.match(SpaceOperation('type', [v], c))
        if isinstance(c.content, Constant):
            return c.content.value
        else:
            return None

    def get_opresult(self, opname, args):
        c = Cell()
        self.match(SpaceOperation(opname, args, c))
        if isinstance(c.content, Constant):
            return c.content.value
        else:
            return None


def annotation_assign(ann1, ann2):
    """Assignment (ann1 = ann2).  All empty cells in 'ann1' are set to the
    value found in 'ann2'.  Returns False if the two annotations are not
    compatible."""
    functor1 = ann1.opname, len(ann1.args)
    functor2 = ann2.opname, len(ann2.args)
    return functor1 == functor2 and same_functor_assign(ann1, ann2)

def same_functor_assign(ann1, ann2):
    """Assignment (ann1 = ann2).  All empty cells in 'ann1' are set to the
    value found in 'ann2'.  Returns False if the variables and constants
    in the two annotations are not compatible.  Assumes that the two
    annotations have the same functor."""
    pairs = zip(ann1.args + [ann1.result], ann2.args + [ann2.result])
    for a1, a2 in pairs:
        v1 = deref(a1)
        if not isinstance(v1, Cell):
            v2 = deref(a2)
            if not isinstance(v2, Cell) and v2 != v1:
                return False
    # match! Set the Cells of ann1...
    for a1, a2 in pairs:
        v1 = deref(a1)
        if isinstance(v1, Cell):
            v1.set(a2)
    return True

def deref(x):
    """If x is a Cell, return the content of the Cell,
    or the Cell itself if empty.  For other x, return x."""
    if isinstance(x, Cell) and x.content is not None:
        return x.content
    else:
        return x
