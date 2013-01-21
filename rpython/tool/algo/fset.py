__all__ = ['FSet', 'emptyset']

# Reference:
#   "Implementing sets efficiently in a functional language"
#   http://swiss.csail.mit.edu/~adams/BB/
#   See BB.sml in the current directory.


class FSet(object):
    """Functional Set.
    Behaves like a frozenset from Python 2.4 (incomplete, though).
    This version is meant to have a better complexity than frozenset for
    operations involving a lot of single-element adds and unions.
    For example, a long chain of 'set.union([x]).union([y]).union([z])...'
    takes quadratic time with frozensets, but only n*log(n) with FSets.
    """
    __slots__ = ['_left', '_value', '_right', '_count']

    def __new__(cls, items=()):
        if isinstance(items, FSet):
            return items
        items = list(items)
        if len(items) == 1:
            return node(emptyset, items[0], emptyset)
        if not items:
            return emptyset
        items.sort()
        any = items[0]
        items = [x for i, x in enumerate(items) if x != items[i-1]]
        if not items:
            items.append(any)
        def maketree(start, stop):
            if start == stop:
                return emptyset
            else:
                mid = (start+stop)//2
                return node(maketree(start, mid), items[mid],
                            maketree(mid+1, stop))
        return maketree(0, len(items))

    def __len__(self):
        return self._count

    def __repr__(self):
        return '{%s}' % (', '.join([repr(n) for n in self]),)

    def __iter__(self):
        return treeiter(self)

    def union(self, other):
        return uniontree(self, FSet(other))

    def __or__(self, other):
        if not isinstance(other, FSet):
            return NotImplemented
        return uniontree(self, other)

    def __eq__(self, other):
        if not isinstance(other, FSet):
            return NotImplemented
        if self is other:
            return True
        if eqtree(self, other):
            other._left = self._left
            other._value = self._value
            other._right = self._right
            return True
        return False

    def __ne__(self, other):
        res = self.__eq__(other)
        if res is NotImplemented:
            return NotImplemented
        return not res

    def __hash__(self):
        return hash(tuple(self)) ^ 1043498183

    def __contains__(self, value):
        return contains(self, value)

emptyset = object.__new__(FSet)
emptyset._count = 0

# ____________________________________________________________
# creation and balancing stuff

WEIGHT = 3

def node(left, value, right):
    result = object.__new__(FSet)
    result._left = left
    result._value = value
    result._right = right
    result._count = left._count + right._count + 1
    return result

def node_balance_fast(left, value, right):
    # used when an original tree was balanced, and changed by at most
    # one element (as in adding or deleting one item).
    ln = left._count
    rn = right._count
    if ln <= 1 and rn <= 1:
        return node(left, value, right)
    elif rn > WEIGHT * ln:   # right too big
        if right._left._count < right._right._count:
            return single_L(left, value, right)
        else:
            return double_L(left, value, right)
    elif ln > WEIGHT * rn:   # left too big
        if left._right._count < left._left._count:
            return single_R(left, value, right)
        else:
            return double_R(left, value, right)
    else:
        return node(left, value, right)

def node_balance(left, value, right):
    if left is emptyset:
        return add(right, value)
    elif right is emptyset:
        return add(left, value)
    elif WEIGHT * left._count < right._count:
        t = node_balance(left, value, right._left)
        return node_balance_fast(t, right._value, right._right)
    elif WEIGHT * right._count < left._count:
        t = node_balance(left._right, value, right)
        return node_balance_fast(left._left, left._value, t)
    else:
        return node(left, value, right)

def add(tree, value):
    if tree is emptyset:
        return node(emptyset, value, emptyset)
    elif value < tree._value:
        t = add(tree._left, value)
        return node_balance_fast(t, tree._value, tree._right)
    elif value == tree._value:
        return tree
    else:
        t = add(tree._right, value)
        return node_balance_fast(tree._left, tree._value, t)

def single_L(left, value, right):
    return node(node(left, value, right._left), right._value, right._right)

def single_R(left, value, right):
    return node(left._left, left._value, node(left._right, value, right))

def double_L(left, value, right):
    rl = right._left
    n1 = node(left, value, rl._left)
    n2 = node(rl._right, right._value, right._right)
    return node(n1, rl._value, n2)

def double_R(left, value, right):
    lr = left._right
    n1 = node(left._left, left._value, lr._left)
    n2 = node(lr._right, value, right)
    return node(n1, lr._value, n2)

# ____________________________________________________________
# union

def uniontree(tree1, tree2):
    if tree2._count <= 1:
        if tree2 is emptyset:
            return tree1
        else:
            return add(tree1, tree2._value)
    elif tree1._count <= 1:
        if tree1 is emptyset:
            return tree2
        else:
            return add(tree2, tree1._value)
    else:
        left2, right2 = splittree(tree2, tree1._value)
        return node_balance(uniontree(tree1._left, left2), tree1._value,
                            uniontree(tree1._right, right2))

def splittree(tree, value):
    if tree is emptyset:
        return emptyset, emptyset
    elif tree._value < value:
        t1, t2 = splittree(tree._right, value)
        return node_balance(tree._left, tree._value, t1), t2
    elif tree._value == value:
        return tree._left, tree._right
    else:
        t1, t2 = splittree(tree._left, value)
        return t1, node_balance(t2, tree._value, tree._right)

# ____________________________________________________________
# utilities

def treeiter(tree):
    if tree is emptyset:
        return
    path = []
    while True:
        while tree._left is not emptyset:
            path.append(tree)
            tree = tree._left
        yield tree._value
        tree = tree._right
        while tree is emptyset:
            if not path:
                return
            tree = path.pop()
            yield tree._value
            tree = tree._right

def eqtree(tree1, tree2):
    if tree1 is tree2:
        return True
    if tree1._count != tree2._count:
        return False
    assert tree1 is not emptyset and tree2 is not emptyset
    left2, right2 = splittree(tree2, tree1._value)
    if left2._count + right2._count == tree2._count:
        return False    # _value was not in tree2
    return eqtree(tree1._left, left2) and eqtree(tree1._right, right2)

def contains(tree, value):
    while tree is not emptyset:
        if value < tree._value:
            tree = tree._left
        elif value == tree._value:
            return True
        else:
            tree = tree._right
    return False


_no = object()
def checktree(tree, bmin=_no, bmax=_no):
    if tree is not emptyset:
        if bmin is not _no:
            assert bmin < tree._value
        if bmax is not _no:
            assert tree._value < bmax
        assert tree._count == tree._left._count + tree._right._count + 1
        checktree(tree._left, bmin, tree._value)
        checktree(tree._right, tree._value, bmax)
