# Original Algorithm:
# By Steve Hanov, 2011. Released to the public domain.
# Please see http://stevehanov.ca/blog/index.php?id=115 for the accompanying article.
#
# Adapted for RPython by cfbolz
#
# Based on Daciuk, Jan, et al. "Incremental construction of minimal acyclic finite-state automata."
# Computational linguistics 26.1 (2000): 3-16.
#
# Updated 2014 to use DAWG as a mapping; see
# Kowaltowski, T.; CL. Lucchesi (1993), "Applications of finite automata representing large vocabularies",
# Software-Practice and Experience 1993

from pprint import pprint
from collections import defaultdict
import sys
import time


# This class represents a node in the directed acyclic word graph (DAWG). It
# has a list of edges to other nodes. It has functions for testing whether it
# is equivalent to another node. Nodes are equivalent if they have identical
# edges, and each identical edge leads to identical states. The __hash__ and
# __eq__ functions allow it to be used as a key in a python dictionary.


class DawgNode(object):

    def __init__(self, dawg):
        self.id = dawg.next_id
        dawg.next_id += 1
        self.final = False
        self.edges = {}

        # Number of end nodes reachable from this one.
        self.count = 0

        self.linear_edges = None # later: list of (char, string, next_state)

    def __str__(self):
        if self.final:
            arr = ["1"]
        else:
            arr = ["0"]

        for (label, node) in sorted(self.edges.items()):
            arr.append(label)
            arr.append(str(node.id))

        return "_".join(arr)
    __repr__ = __str__

    def __hash__(self):
        return self.__str__().__hash__()

    def __eq__(self, other):
        return self.__str__() == other.__str__()

    def num_reachable(self):
        # if a count is already assigned, return it
        if self.count:
            return self.count

        # count the number of final nodes that are reachable from this one.
        # including self
        count = 0
        if self.final:
            count += 1
        for label, node in self.edges.items():
            count += node.num_reachable()

        self.count = count
        return count


class Dawg(object):
    def __init__(self):
        self.previous_word = ""
        self.next_id = 0
        self.root = DawgNode(self)

        # Here is a list of nodes that have not been checked for duplication.
        self.unchecked_nodes = []

        # Here is a list of unique nodes that have been checked for
        # duplication.
        self.minimized_nodes = {}

        # Here is the data associated with all the nodes
        self.data = []

        # and here's the inverse dict from data back to node numbers
        self.inverse = {}

    def insert(self, word, data):
        assert [0 <= ord(c) < 128 for c in word]
        if word <= self.previous_word:
            raise Exception("Error: Words must be inserted in alphabetical order.")
        if data in self.inverse:
            raise Exception("data %s is duplicate, got it for word %s and now %s" % (data, self.inverse, word))

        # find common prefix between word and previous word
        common_prefix = 0
        for i in range(min(len(word), len(self.previous_word))):
            if word[i] != self.previous_word[i]:
                break
            common_prefix += 1

        # Check the unchecked_nodes for redundant nodes, proceeding from last
        # one down to the common prefix size. Then truncate the list at that
        # point.
        self._minimize(common_prefix)

        self.inverse[data] = len(self.data)
        self.data.append(data)

        # add the suffix, starting from the correct node mid-way through the
        # graph
        if len(self.unchecked_nodes) == 0:
            node = self.root
        else:
            node = self.unchecked_nodes[-1][2]

        for letter in word[common_prefix:]:
            next_node = DawgNode(self)
            node.edges[letter] = next_node
            self.unchecked_nodes.append((node, letter, next_node))
            node = next_node

        node.final = True
        self.previous_word = word

    def finish(self):
        # minimize all unchecked_nodes
        self._minimize(0)

        # go through entire structure and assign the counts to each node.
        self.root.num_reachable()

        # turn it into a cdawg
        return self.cdawgify()

    def _minimize(self, down_to):
        # proceed from the leaf up to a certain point
        for i in range(len(self.unchecked_nodes) - 1, down_to - 1, -1):
            (parent, letter, child) = self.unchecked_nodes[i]
            if child in self.minimized_nodes:
                # replace the child with the previously encountered one
                parent.edges[letter] = self.minimized_nodes[child]
            else:
                # add the state to the minimized nodes.
                self.minimized_nodes[child] = child
            self.unchecked_nodes.pop()

    def lookup(self, word):
        node = self.root
        skipped = 0  # keep track of number of final nodes that we skipped
        for letter in word:
            if letter not in node.edges:
                return None
            for label, child in sorted(node.edges.items()):
                if label == letter:
                    if node.final:
                        skipped += 1
                    node = child
                    break
                skipped += child.count

        if node.final:
            return self.data[skipped]

    def enum_all_nodes(self):
        stack = [self.root]
        done = set()
        while stack:
            node = stack.pop()
            if node.id in done:
                continue
            yield node
            done.add(node.id)
            for label, child in sorted(node.edges.items()):
                stack.append(child)

    def prettyprint(self):
        for node in sorted(self.enum_all_nodes(), key=lambda e: e.id):
            print("{}: ({}) {}{}".format(node.id, node, node.count, " final" if node.final else ""))
            for label, child in sorted(node.edges.items()):
                print("    {} goto {}".format(label, child.id))

    def inverse_lookup(self, number):
        pos = self.inverse[number]
        result = []
        node = self.root
        while 1:
            if node.final:
               if pos == 0:
                   return "".join(result)
               pos -= 1
            for label, child in sorted(node.edges.items()):
                nextpos = pos - child.count
                if nextpos < 0:
                    result.append(label)
                    node = child
                    break
                else:
                    pos = nextpos
            else:
                assert 0

    def cdawgify(self):
        # turn the dawg into a compact string representation
        incoming = defaultdict(list)
        for node in sorted(self.enum_all_nodes(), key=lambda e: e.id):
            for label, child in sorted(node.edges.items()):
                incoming[child].append(node)
        for node in sorted(self.enum_all_nodes(), key=lambda e: e.id):
            node.linear_edges = []
            for label, child in sorted(node.edges.items()):
                s = [label]
                while len(child.edges) == 1 and len(incoming[child]) == 1 and not child.final and len(s) < 256:
                    (c, child), = child.edges.items()
                    s.append(c)
                node.linear_edges.append((''.join(s), child))


        def int4(i, r):
            for _ in range(4):
                r.append(chr(i & 0xff))
                i >>= 8
            assert not i

        def int1(i, r):
            r.append(chr(i & 0xff))
            assert not i >> 8

        def size_node(node):
            # 4 size
            # 1 final + num edges
            result = 5

            # per edge:
            # 1 size
            # n chars
            # 4 offset
            for s, edge in node.linear_edges:
                result += 5 + len(s)
            return result

        # assign positions to every reachable linear node
        stack = [self.root]
        positions = {}
        current_offset = 0
        while stack:
            node = stack.pop()
            if node.id in positions:
                continue
            positions[node.id] = node, current_offset
            current_offset += size_node(node)
            for label, child in sorted(node.linear_edges):
                stack.append(child)

        result = []
        for node, offset in positions.values():
            assert len(result) == offset
            int4(node.count, result)
            int1((len(node.linear_edges) << 1) | node.final, result)
            for label, edge in node.linear_edges:
                int1(len(label), result)
                result.extend(label)
                int4(positions[edge.id][1], result)
        return "".join(result), self.data

# ______________________________________________________________________
# the following functions are used from RPython to interpret the packed
# representation

from rpython.rlib import objectmodel

@objectmodel.always_inline
def readint4(packed, node):
    return ord(packed[node]) | (ord(packed[node + 1]) << 8) | (ord(packed[node + 2]) << 16) | (ord(packed[node + 3]) << 24), node + 4

@objectmodel.always_inline
def readint1(packed, node):
    return ord(packed[node]), node + 1

@objectmodel.always_inline
def decode_node(packed, node):
    node_count, node = readint4(packed, node)
    x, node = readint1(packed, node)
    final = bool(x & 1)
    num_edges = x >> 1
    return node_count, final, num_edges, node

@objectmodel.always_inline
def decode_edge(packed, offset):
    size, offset = readint1(packed, offset)
    child_offset, _ = readint4(packed, offset + size)
    return size, child_offset, offset

def lookup(packed, data, s):
    pos = 0
    node = 0
    skipped = 0  # keep track of number of final nodes that we skipped
    false = False
    while pos < len(s):
        node_count, final, num_edges, node = decode_node(packed, node)
        for i in range(num_edges):
            size, child_offset, node = decode_edge(packed, node)
            for i in range(size):
                if packed[node + i] != s[pos + i]:
                    if i > 0: # only the first char can lead to a still valid mismatch
                        raise KeyError
                    break
            else:
                # match
                if final:
                    skipped += 1
                pos += size
                node = child_offset
                break
            child_count, _ = readint4(packed, child_offset)
            skipped += child_count
            node += size + 4
        else:
            raise KeyError
    node_count, final, num_edges, node = decode_node(packed, node)
    if final:
        return data[skipped]
    raise KeyError

def inverse_lookup(packed, inverse, x):
    pos = inverse[x]
    return _inverse_lookup(packed, pos)

def _inverse_lookup(packed, pos):
    from rpython.rlib import rstring
    result = rstring.StringBuilder(42) # max size is like 83
    node = 0
    while 1:
        node_count, final, num_edges, node = decode_node(packed, node)
        if final:
           if pos == 0:
               return result.build()
           pos -= 1
        for i in range(num_edges):
            size, child_offset, node = decode_edge(packed, node)
            child_count, _ = readint4(packed, child_offset)
            nextpos = pos - child_count
            if nextpos < 0:
                assert node >= 0
                assert size >= 0
                result.append_slice(packed, node, node + size)
                node = child_offset
                break
            else:
                pos = nextpos
                node += size + 4
        else:
            raise KeyError

# ______________________________________________________________________
# some functions to efficiently encode the relatively dense
# charcode-to-position dictionary

MAXBLANK = 8
MINLIST = 5

def findranges(d):
    ranges = []
    for i in range(max(d)+1):
        if i in d:
            if not ranges:
                ranges.append((i,i))
                last = i
                continue
            if last + 1 == i:
                ranges[-1] = (ranges[-1][0], i)
            else:
                ranges.append((i,i))
            last = i
    return ranges

def collapse_ranges(ranges):
    collapsed = [ranges[0]]
    for i in range(1, len(ranges)):
        lows, lowe = collapsed[-1]
        highs, highe = ranges[i]
        if highs - lowe < MAXBLANK:
            collapsed[-1] = (lows, highe)
        else:
            collapsed.append(ranges[i])

    return collapsed


# ______________________________________________________________________
# code generation

empty_functions = """
def dawg_lookup(name):
    raise KeyError
def lookup_charcode(code):
    raise KeyError
"""

def build_compression_dawg(outfile, ucdata):
    print >> outfile, "#" + "_" * 60
    print >> outfile, "# output from build_compression_dawg"

    if not ucdata:
        print >> outfile, empty_functions
        return

    d = Dawg()
    for name, value in sorted(ucdata.items()):
        d.insert(name, value)
    packed, pos_to_code = d.finish()
    print "dawg", len(packed), len(pos_to_code)
    print >> outfile, "from rpython.rlib.unicodedata.dawg import lookup as _dawg_lookup, _inverse_lookup"
    print >> outfile, "packed_dawg = ("
    for i in range(0, len(packed), 40):
        print >> outfile, "    %r" % packed[i: i + 40]
    print >> outfile, ")"
    print >> outfile, "pos_to_code = ",
    pprint(pos_to_code, stream=outfile)

    print >> outfile, """
def lookup_charcode(c):
    pos = _charcode_to_pos(c)
    return _inverse_lookup(packed_dawg, pos)

def dawg_lookup(n):
    return _dawg_lookup(packed_dawg, pos_to_code, n)
    """


    function = ["def _charcode_to_pos(code):"]
    reversedict = d.inverse
    ranges = collapse_ranges(findranges(reversedict))
    prefix = ""
    for low, high in ranges:
        if high - low <= 5:
            for code in range(low, high + 1):
                if code in reversedict:
                    function.append(
                        "    %sif code == %d: return %s" %
                        (prefix, code, reversedict[code]))
                    prefix = "el"
            continue

        function.append(
            "    %sif %d <= code <= %d: return _charcode_to_pos_%d[code-%d]" % (
            prefix, low, high, low, low))
        prefix = "el"

        print >> outfile, "_charcode_to_pos_%d = [" % (low,)
        for code in range(low, high + 1):
            if code in reversedict:
                print >> outfile, "%s," % (reversedict[code], )
            else:
                print >> outfile, "-1,"
        print >> outfile, "]\n"
    function.append("    raise KeyError(code)")
    print >> outfile, '\n'.join(function)
