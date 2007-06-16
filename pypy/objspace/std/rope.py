import py
import sys
from pypy.rlib.rarithmetic import intmask, _hash_string, ovfcheck
from pypy.rlib.objectmodel import we_are_translated
import math

LOG2 = math.log(2)
NBITS = int(math.log(sys.maxint) / LOG2) + 2

# XXX should optimize the numbers
NEW_NODE_WHEN_LENGTH = 16
MAX_DEPTH = 32 # maybe should be smaller
MIN_SLICE_LENGTH = 64
CONCATENATE_WHEN_MULTIPLYING = 128
HIGHEST_BIT_SET = intmask(1L << (NBITS - 1))

def find_fib_index(l):
    if l == 0:
        return -1
    a, b = 1, 2
    i = 0
    while 1:
        if a <= l < b:
            return i
        a, b = b, a + b
        i += 1

def masked_power(a, b):
    if b == 0:
        return 1
    if b == 1:
        return a
    if a == 0:
        return 0
    if a == 1:
        return 1
    num_bits = 2
    mask = b >> 2
    while mask:
        num_bits += 1
        mask >>= 1
    result = a
    mask = 1 << (num_bits - 2)
    #import pdb; pdb.set_trace()
    for i in range(num_bits - 1):
        if mask & b:
            result = intmask(result * result * a)
        else:
            result = intmask(result * result)
        mask >>= 1
    return result


class StringNode(object):
    hash_cache = 0
    def length(self):
        return 0

    def depth(self):
        return 0

    def rebalance(self):
        return self

    def hash_part(self):
        raise NotImplementedError("base class")

    def flatten(self):
        return ''

    def __add__(self, other):
        return concatenate(self, other)
    
    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(self.length())
            # XXX sucks
            slicelength = len(xrange(start, stop, step))
            return getslice(self, start, stop, step, slicelength)
        return self.getitem(index)

    def getitem(self, index):
        raise NotImplementedError("abstract base class")

    def getitem_slice(self, start, stop):
        # XXX really horrible, in most cases
        result = []
        for i in range(start, stop):
            result.append(self.getitem(i))
        return rope_from_charlist(result)

    def view(self):
        view([self])

    def check_balanced(self):
        return True


class LiteralStringNode(StringNode):
    def __init__(self, s):
        self.s = s
    
    def length(self):
        return len(self.s)

    def flatten(self):
        return self.s

    def hash_part(self):
        h = self.hash_cache
        if not h:
            x = 0
            for c in self.s:
                x = (1000003*x) + ord(c)
            x = intmask(x)
            x |= HIGHEST_BIT_SET
            h = self.hash_cache = x
        return h

    def getitem(self, index):
        return self.s[index]

    def getitem_slice(self, start, stop):
        assert 0 <= start <= stop
        return LiteralStringNode(self.s[start:stop])

    def dot(self, seen, toplevel=False):
        if self in seen:
            return
        seen[self] = True
        addinfo = str(self.s).replace('"', "'") or "_"
        if len(addinfo) > 10:
            addinfo = addinfo[:3] + "..." + addinfo[-3:]
        yield ('"%s" [shape=box,label="length: %s\\n%s"];' % (
            id(self), len(self.s),
            repr(addinfo).replace('"', '').replace("\\", "\\\\")))


class BinaryConcatNode(StringNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        try:
            self.len = ovfcheck(left.length() + right.length())
        except OverflowError:
            raise
        self._depth = max(left.depth(), right.depth()) + 1
        self.balanced = False

    def check_balanced(self):
        if self.balanced:
            return True
        if not self.left.check_balanced() or not self.right.check_balanced():
            return False
        left = self.left
        right = self.right
        llen = left.length()
        rlen = right.length()
        ldepth = left.depth()
        rdepth = right.depth()
        balanced = (find_fib_index(self.len // (NEW_NODE_WHEN_LENGTH / 2)) >=
                    self._depth)
        self.balanced = balanced
        return balanced

    def length(self):
        return self.len

    def depth(self):
        return self._depth

    def getitem(self, index):
        llen = self.left.length()
        if index >= llen:
            return self.right.getitem(index - llen)
        else:
            return self.left.getitem(index)

    def flatten(self):
        f = fringe(self)
        return "".join([node.flatten() for node in f])
 
    def hash_part(self):
        h = self.hash_cache
        if not h:
            h1 = self.left.hash_part()
            h2 = self.right.hash_part()
            x = intmask(h2 + h1 * (masked_power(1000003, self.right.length())))
            x |= HIGHEST_BIT_SET
            h = self.hash_cache = x
        return h

    def rebalance(self):
        return rebalance([self], self.len)

    def dot(self, seen, toplevel=False):
        if self in seen:
            return
        seen[self] = True
        if toplevel:
            addition = ", fillcolor=red"
        elif self.check_balanced():
            addition = ", fillcolor=yellow"
        else:
            addition = ""
        yield '"%s" [shape=octagon,label="+\\ndepth=%s, length=%s"%s];' % (
                id(self), self._depth, self.len, addition)
        for child in [self.left, self.right]:
            yield '"%s" -> "%s";' % (id(self), id(child))
            for line in child.dot(seen):
                yield line

class SliceNode(StringNode):
    def __init__(self, start, stop, node):
        assert 0 <= start <= stop
        self.start = start
        self.stop = stop
        self.node = node

    def length(self):
        return self.stop - self.start

    def getitem_slice(self, start, stop):
        return self.node.getitem_slice(self.start + start, self.start + stop)

    def getitem(self, index):
        return self.node.getitem(self.start + index)

    def flatten(self):
        return self.node.flatten()[self.start: self.stop]

    def hash_part(self):
        h = self.hash_cache
        if not h:
            x = 0
            for i in range(self.start, self.stop):
                x = (1000003*x) + ord(self.node.getitem(i))
            x = intmask(x)
            x |= HIGHEST_BIT_SET
            h = self.hash_cache = x
        return h

    def dot(self, seen, toplevel=False):
        if self in seen:
            return
        seen[self] = True
        yield '"%s" [shape=octagon,label="slice\\nstart=%s, stop=%s"];' % (
                id(self), self.start, self.stop)
        yield '"%s" -> "%s";' % (id(self), id(self.node))
        for line in self.node.dot(seen):
            yield line

class EfficientGetitemWraper(StringNode):
    def __init__(self, node):
        assert isinstance(node, BinaryConcatNode)
        self.node = node
        self.iter = SeekableCharIterator(node)
        self.nextpos = 0
        self.accesses = 0
        self.seeks = 0

    def length(self):
        return self.node.length()

    def depth(self):
        return self.node.depth()

    def rebalance(self):
        return EfficientGetitemWraper(self.node.rebalance())

    def hash_part(self):
        return self.node.hash_part()

    def flatten(self):
        return self.node.flatten()

    def getitem(self, index):
        self.accesses += 1
        nextpos = self.nextpos
        self.nextpos = index + 1
        if index < nextpos:
            self.iter.seekback(nextpos - index)
            self.seeks += nextpos - index
        elif index > nextpos:
            self.iter.seekforward(index - nextpos)
            self.seeks += index - nextpos
        return self.iter.next()

    def view(self):
        return self.node.view()

    def check_balanced(self):
        return self.node.check_balanced()


def concatenate(node1, node2):
    if node1.length() == 0:
        return node2
    if node2.length() == 0:
        return node1
    if (isinstance(node2, LiteralStringNode) and
        len(node2.s) <= NEW_NODE_WHEN_LENGTH):
        if isinstance(node1, LiteralStringNode):
            if len(node1.s) + len(node2.s) <= NEW_NODE_WHEN_LENGTH:
                return LiteralStringNode(node1.s + node2.s)
        elif isinstance(node1, BinaryConcatNode):
            r = node1.right
            if isinstance(r, LiteralStringNode):
                if len(r.s) + len(node2.s) <= NEW_NODE_WHEN_LENGTH:
                    return BinaryConcatNode(node1.left,
                                            LiteralStringNode(r.s + node2.s))
    result = BinaryConcatNode(node1, node2)
    if result.depth() > MAX_DEPTH: #XXX better check
        return result.rebalance()
    return result

def getslice(node, start, stop, step, slicelength):
    if step != 1:
        start, stop, node = find_straddling(node, start, stop)
        iter = SeekableCharIterator(node)
        iter.seekforward(start)
        result = [iter.next()]
        for i in range(slicelength - 1):
            iter.seekforward(step - 1)
            result.append(iter.next())
        return rope_from_charlist(result)
    return getslice_one(node, start, stop)

def getslice_one(node, start, stop):
    start, stop, node = find_straddling(node, start, stop)
    if isinstance(node, BinaryConcatNode):
        if start == 0:
            if stop == node.length():
                return node
            return getslice_left(node, stop)
        if stop == node.length():
            return getslice_right(node, start)
        return concatenate(
            getslice_right(node.left, start),
            getslice_left(node.right, stop - node.left.length()))
    else:
        return getslice_primitive(node, start, stop)

def find_straddling(node, start, stop):
    while 1:
        if isinstance(node, BinaryConcatNode):
            llen = node.left.length()
            if start >= llen:
                node = node.right
                start = start - llen
                stop = stop - llen
                continue
            if stop <= llen:
                node = node.left
                continue
        return start, stop, node

def getslice_right(node, start):
    while 1:
        if start == 0:
            return node
        if isinstance(node, BinaryConcatNode):
            llen = node.left.length()
            if start >= llen:
                node = node.right
                start = start - llen
                continue
            else:
                return concatenate(getslice_right(node.left, start),
                                   node.right)
        return getslice_primitive(node, start, node.length())

def getslice_left(node, stop):
    while 1:
        if stop == node.length():
            return node
        if isinstance(node, BinaryConcatNode):
            llen = node.left.length()
            if stop <= llen:
                node = node.left
                continue
            else:
                return concatenate(node.left,
                                   getslice_left(node.right, stop - llen))
        return getslice_primitive(node, 0, stop)


def getslice_primitive(node, start, stop):
    if stop - start >= MIN_SLICE_LENGTH:
        if isinstance(node, SliceNode):
            return SliceNode(start + node.start, stop + node.start,
                             node.node)
        return SliceNode(start, stop, node)
    return node.getitem_slice(start, stop)

def multiply(node, times):
    if times <= 0:
        return LiteralStringNode("")
    if times == 1:
        return node
    end_length = node.length() * times
    num_bits = 2
    mask = times >> 2
    while mask:
        num_bits += 1
        mask >>= 1
    result = node
    mask = 1 << (num_bits - 2)
    #import pdb; pdb.set_trace()
    for i in range(num_bits - 1):
        if mask & times:
            if result.length() < CONCATENATE_WHEN_MULTIPLYING:
                result = concatenate(result, result)
                result = concatenate(result, node)
            else:
                result = BinaryConcatNode(result, result)
                result = BinaryConcatNode(result, node)
        else:
            if result.length() < CONCATENATE_WHEN_MULTIPLYING:
                result = concatenate(result, result)
            else:
                result = BinaryConcatNode(result, result)
        mask >>= 1
    return result

def join(node, l):
    if node.length() == 0:
        return rebalance(l)
    nodelist = [None] * (2 * len(l) - 1)
    length = 0
    for i in range(len(l)):
        nodelist[2 * i] = l[i]
        length += l[i].length()
    for i in range(len(l) - 1):
        nodelist[2 * i + 1] = node
    length += (len(l) - 1) * node.length()
    return rebalance(nodelist, length)

def rebalance(nodelist, sizehint=-1):
    nodelist.reverse()
    if sizehint < 0:
        sizehint = 0
        for node in nodelist:
            sizehint += node.length()
    if sizehint == 0:
        return LiteralStringNode("")

    # this code is based on the Fibonacci identity:
    #   sum(fib(i) for i in range(n+1)) == fib(n+2)
    l = [None] * (find_fib_index(sizehint) + 2)
    stack = nodelist
    empty_up_to = len(l)
    a = b = sys.maxint
    first_node = None
    while stack:
        curr = stack.pop()
        while isinstance(curr, BinaryConcatNode) and not curr.balanced:
            stack.append(curr.right)
            curr = curr.left

        currlen = curr.length()
        if currlen == 0:
            continue

        if currlen < a:
            # we can put 'curr' to its preferred location, which is in
            # the known empty part at the beginning of 'l'
            a, b = 1, 2
            empty_up_to = 0
            while not (currlen < b):
                empty_up_to += 1
                a, b = b, a+b
        else:
            # sweep all elements up to the preferred location for 'curr'
            while not (currlen < b and l[empty_up_to] is None):
                if l[empty_up_to] is not None:
                    curr = concatenate(l[empty_up_to], curr)
                    l[empty_up_to] = None
                    currlen = curr.length()
                else:
                    empty_up_to += 1
                    a, b = b, a+b

        if empty_up_to == len(l):
            return curr
        l[empty_up_to] = curr
        first_node = curr

    # sweep all elements
    curr = first_node
    for index in range(empty_up_to + 1, len(l)):
        if l[index] is not None:
            curr = BinaryConcatNode(l[index], curr)
    assert curr is not None
    curr.check_balanced()
    return curr

# __________________________________________________________________________
# construction from normal strings

def rope_from_charlist(charlist):
    nodelist = []
    size = 0
    for i in range(0, len(charlist), NEW_NODE_WHEN_LENGTH):
        chars = charlist[i: min(len(charlist), i + NEW_NODE_WHEN_LENGTH)]
        nodelist.append(LiteralStringNode("".join(chars)))
        size += len(chars)
    return rebalance(nodelist, size)

# __________________________________________________________________________
# searching

def find_char(node, c, start=0, stop=-1):
    offset = 0
    length = node.length()
    if stop == -1:
        stop = length
    if start != 0 or stop != length:
        newstart, newstop, node = find_straddling(node, start, stop)
        offset = start - newstart
        start = newstart
        stop = newstop
    assert 0 <= start <= stop
    if isinstance(node, LiteralStringNode):
        result = node.s.find(c, start, stop)
        if result == -1:
            return -1
        return result + offset
    elif isinstance(node, SliceNode):
        return find_char(node.node, c, node.start + start,
                         node.start + stop) - node.start + offset
    iter = FringeIterator(node)
    #import pdb; pdb.set_trace()
    i = 0
    while i < stop:
        try:
            fringenode = iter.next()
        except StopIteration:
            return -1
        nodelength = fringenode.length()
        if i + nodelength <= start:
            i += nodelength
            continue
        searchstart = max(0, start - i)
        searchstop = min(stop - i, nodelength)
        if isinstance(fringenode, LiteralStringNode):
            st = fringenode.s
            localoffset = 0
        else:
            assert isinstance(fringenode, SliceNode)
            n = fringenode.node
            assert isinstance(n, LiteralStringNode)
            st = n.s
            localoffset = -fringenode.start
            searchstart += fringenode.start
            searchstop += fringenode.stop
        pos = st.find(c, searchstart, searchstop)
        if pos != -1:
            return pos + i + offset + localoffset
        i += nodelength
    return -1

def find(node, subnode, start=0, stop=-1):

    len1 = node.length()
    if stop > len1 or stop == -1:
        stop = len1
    substring = subnode.flatten() # XXX stressful to do it as a node
    len2 = len(substring)
    if len2 == 1:
        return find_char(node, substring[0], start, stop)
    if len2 == 0:
        if (stop - start) < 0:
            return -1
        return start
    restart = construct_restart_positions(substring)
    return _find(node, substring, start, stop, restart)

def _find(node, substring, start, stop, restart):
    len2 = len(substring)
    i = 0
    m = start
    iter = SeekableCharIterator(node)
    iter.seekforward(start)
    c = iter.next()
    while m + i < stop:
        if c == substring[i]:
            i += 1
            if i == len2:
                return m
            if m + i < stop:
                c = iter.next()
        else:
            # mismatch, go back to the last possible starting pos
            if i==0:
                m += 1
                if m + i < stop:
                    c = iter.next()
            else:
                e = restart[i-1]
                new_m = m + i - e
                assert new_m <= m + i
                seek = m + i - new_m
                if seek:
                    iter.seekback(m + i - new_m)
                    c = iter.next()
                m = new_m
                i = e
    return -1

def construct_restart_positions(s):
    l = len(s)
    restart = [0] * l
    restart[0] = 0
    i = 1
    j = 0
    while i < l:
        if s[i] == s[j]:
            j += 1
            restart[i] = j
            i += 1
        elif j>0:
            j = restart[j-1]
        else:
            restart[i] = 0
            i += 1
            j = 0
    return restart

def construct_restart_positions_node(node):
    # really a bit overkill
    l = node.length()
    restart = [0] * l
    restart[0] = 0
    i = 1
    j = 0
    iter1 = CharIterator(node)
    iter1.next()
    c1 = iter1.next()
    iter2 = SeekableCharIterator(node)
    c2 = iter2.next()
    while i < l:
        if c1 == c2:
            j += 1
            if j != l:
                c2 = iter2.next()
            restart[i] = j
            i += 1
            if i != l:
                c1 = iter1.next()
            else:
                break
        elif j>0:
            new_j = restart[j-1]
            assert new_j < j
            iter2.seekback(j - new_j)
            c2 = iter2.next()
            j = new_j
        else:
            restart[i] = 0
            i += 1
            if i != l:
                c1 = iter1.next()
            else:
                break
            j = 0
            iter2 = SeekableCharIterator(node)
            c2 = iter2.next()
    return restart

def view(objs):
    from dotviewer import graphclient
    content = ["digraph G{"]
    seen = {}
    for i, obj in enumerate(objs):
        if obj is None:
            content.append(str(i) + ";")
        else:
            content.extend(obj.dot(seen, toplevel=True))
    content.append("}")
    p = py.test.ensuretemp("automaton").join("temp.dot")
    p.write("\n".join(content))
    graphclient.display_dot_file(str(p))


# __________________________________________________________________________
# iteration

class FringeIterator(object):
    def __init__(self, node):
        self.stack = [node]

    def next(self):
        while self.stack:
            curr = self.stack.pop()
            while 1:
                if isinstance(curr, BinaryConcatNode):
                    self.stack.append(curr.right)
                    curr = curr.left
                else:
                    return curr
        raise StopIteration

def fringe(node):
    result = []
    iter = FringeIterator(node)
    while 1:
        try:
            result.append(iter.next())
        except StopIteration:
            return result

class SeekableFringeIterator(object):
    # XXX allow to seek in bigger character steps
    def __init__(self, node):
        self.stack = [node]
        self.fringestack = []
        self.fringe = []

    def next(self):
        if self.fringestack:
            result = self.fringestack.pop()
            self.fringe.append(result)
            return result
        while self.stack:
            curr = self.stack.pop()
            while 1:
                if isinstance(curr, BinaryConcatNode):
                    self.stack.append(curr.right)
                    curr = curr.left
                else:
                    self.fringe.append(curr)
                    return curr
        raise StopIteration

    def seekback(self):
        result = self.fringe.pop()
        self.fringestack.append(result)
        return result


class CharIterator(object):
    def __init__(self, node):
        self.iter = FringeIterator(node)
        self.node = None
        self.nodelength = 0
        self.index = 0

    def next(self):
        node = self.node
        if node is None:
            while 1:
                node = self.node = self.iter.next()
                nodelength = self.nodelength = node.length()
                if nodelength != 0:
                    break
            self.index = 0
        index = self.index
        result = self.node.getitem(index)
        if self.index == self.nodelength - 1:
            self.node = None
        else:
            self.index = index + 1
        return result

class SeekableCharIterator(object):
    def __init__(self, node):
        self.iter = SeekableFringeIterator(node)
        self.node = self.nextnode()
        self.nodelength = self.node.length()
        self.index = 0

    def nextnode(self):
        while 1:
            node = self.node = self.iter.next()
            nodelength = self.nodelength = node.length()
            if nodelength != 0:
                break
        self.index = 0
        return node

    def next(self):
        node = self.node
        if node is None:
            node = self.nextnode()
        index = self.index
        result = self.node.getitem(index)
        if self.index == self.nodelength - 1:
            self.node = None
        self.index = index + 1
        return result

    def seekforward(self, numchars):
        if numchars < (self.nodelength - self.index):
            self.index += numchars
            return
        numchars -= self.nodelength - self.index
        while 1:
            node = self.iter.next()
            length = node.length()
            if length <= numchars:
                numchars -= length
            else:
                self.index = numchars
                self.node = node
                self.nodelength = node.length()
                return
        
    def seekback(self, numchars):
        if numchars <= self.index:
            self.index -= numchars
            if self.node is None:
                self.iter.seekback()
                self.node = self.iter.next()
            return
        numchars -= self.index
        self.iter.seekback() # for first item
        while 1:
            node = self.iter.seekback()
            length = node.length()
            if length < numchars:
                numchars -= length
            else:
                self.index = length - numchars
                self.node = self.iter.next()
                self.nodelength = self.node.length()
                return

class FindIterator(object):
    def __init__(self, node, sub, start=0, stop=-1):
        self.node = node
        len1 = self.length = node.length()
        substring = self.substring = sub.flatten() # XXX for now
        len2 = len(substring)
        self.search_length = len2
        if len2 == 0:
            self.restart_positions = None
        elif len2 == 1:
            self.restart_positions = None
        else:
            self.restart_positions = construct_restart_positions(substring)
        self.start = start
        if stop == -1 or stop > len1:
            stop = len1
        self.stop = stop
    
    def next(self):
        if self.search_length == 0:
            if (self.stop - self.start) < 0:
                raise StopIteration
            start = self.start
            self.start += 1
            return start
        elif self.search_length == 1:
            result = find_char(self.node, self.substring[0],
                               self.start, self.stop)
            if result == -1:
                self.start = self.length
                raise StopIteration
            self.start = result + 1
            return result
        if self.start >= self.stop:
            raise StopIteration
        result = _find(self.node, self.substring, self.start,
                       self.stop, self.restart_positions)
        if result == -1:
            self.start = self.length
            raise StopIteration
        self.start = result + self.search_length
        return result

# __________________________________________________________________________
# comparison


def eq(node1, node2):
    if node1 is node2:
        return True
    if node1.length() != node2.length():
        return False
    if hash_rope(node1) != hash_rope(node2):
        return False
    if (isinstance(node1, LiteralStringNode) and
        isinstance(node2, LiteralStringNode)):
        return node1.s == node2.s
    iter1 = CharIterator(node1)
    iter2 = CharIterator(node2)
    # XXX could be cleverer and detect partial equalities
    while 1:
        try:
            c = iter1.next()
        except StopIteration:
            return True
        if c != iter2.next():
            return False

def compare(node1, node2):
    len1 = node1.length()
    len2 = node2.length()
    if not len1:
        if not len2:
            return 0
        return -1
    if not len2:
        return 1

    if len1 < len2:
        cmplen = len1
    else:
        cmplen = len2
    i = 0
    iter1 = CharIterator(node1)
    iter2 = CharIterator(node2)
    while i < cmplen:
        diff = ord(iter1.next()) - ord(iter2.next())
        if diff != 0:
            return diff
        i += 1
    return len1 - len2


# __________________________________________________________________________
# misc

def hash_rope(rope):
    length = rope.length()
    if length == 0:
        return -1
    x = rope.hash_part()
    x <<= 1 # get rid of the bit that is always set
    x ^= ord(rope.getitem(0))
    x ^= rope.length()
    return intmask(x)
