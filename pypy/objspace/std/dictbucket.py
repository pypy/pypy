from pypy.objspace.std.dictmultiobject import DictImplementation
from pypy.objspace.std.dictmultiobject import IteratorImplementation


class BucketNode:
    def __init__(self, hash, w_key, w_value, next):
        self.hash = hash
        self.w_key = w_key
        self.w_value = w_value
        self.next = next


DISTRIBUTE = 9


class BucketDictImplementation(DictImplementation):

    def __init__(self, space):
        self.space = space
        self.len = 0
        self.table = [None] * 4

    def __repr__(self):
        bs = []
        for node in self.table:
            count = 0
            while node is not None:
                count += 1
                node = node.next
            bs.append(str(count))
        return "%s<%s>" % (self.__class__.__name__, ', '.join(bs))

    def get(self, w_key):
        space = self.space
        hash = space.hash_w(w_key)
        index = (hash * DISTRIBUTE) & (len(self.table) - 1)
        node = self.table[index]
        while node is not None:
            if node.hash == hash and space.eq_w(w_key, node.w_key):
                return node.w_value
            node = node.next
        return None

    def setitem(self, w_key, w_value):
        space = self.space
        hash = space.hash_w(w_key)
        index = (hash * DISTRIBUTE) & (len(self.table) - 1)
        node = head = self.table[index]
        while node is not None:
            if node.hash == hash and space.eq_w(w_key, node.w_key):
                node.w_value = w_value
                return self
            node = node.next
        self.table[index] = BucketNode(hash, w_key, w_value, head)
        self.len += 1
        if self.len > len(self.table):
            self._resize()
        return self

    def setitem_str(self, w_key, w_value, shadows_type=True):
        return self.setitem(w_key, w_value)

    def delitem(self, w_key):
        space = self.space
        hash = space.hash_w(w_key)
        index = (hash * DISTRIBUTE) & (len(self.table) - 1)
        node = self.table[index]
        prev = None
        while node is not None:
            if node.hash == hash and space.eq_w(w_key, node.w_key):
                self.len -= 1
                if self.len == 0:
                    return self.space.emptydictimpl
                if prev is None:
                    self.table[index] = node.next
                else:
                    prev.next = node.next
                if self.len < len(self.table) // 2:
                    self._resize()
                return self
            prev = node
            node = node.next
        raise KeyError

    def length(self):
        return self.len

    def _resize(self):
        newsize = 4
        while newsize < self.len:
            newsize *= 2
        newtable = [None] * newsize
        for node in self.table:
            while node is not None:
                newindex = (node.hash * DISTRIBUTE) & (newsize - 1)
                next = node.next
                node.next = newtable[newindex]
                newtable[newindex] = node
                node = next
        self.table = newtable

    def iteritems(self):
        return BucketDictItemIteratorImplementation(self.space, self)
    def iterkeys(self):
        return BucketDictKeyIteratorImplementation(self.space, self)
    def itervalues(self):
        return BucketDictValueIteratorImplementation(self.space, self)

    def keys(self):
        result_w = []
        for node in self.table:
            while node is not None:
                result_w.append(node.w_key)
                node = node.next
        return result_w

    def values(self):
        result_w = []
        for node in self.table:
            while node is not None:
                result_w.append(node.w_value)
                node = node.next
        return result_w

    def items(self):
        space = self.space
        result_w = []
        for node in self.table:
            while node is not None:
                w_item = space.newtuple([node.w_key, node.w_value])
                result_w.append(w_item)
                node = node.next
        return result_w


class BucketDictIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.index = 0
        self.node = None

    def next_entry(self):
        node = self.node
        while node is None:
            table = self.dictimplementation.table
            if self.index >= len(table):
                return None
            node = table[self.index]
            self.index += 1
        self.node = node.next
        return self.get_result(node)


class BucketDictKeyIteratorImplementation(BucketDictIteratorImplementation):
    def get_result(self, node):
        return node.w_key

class BucketDictValueIteratorImplementation(BucketDictIteratorImplementation):
    def get_result(self, node):
        return node.w_value

class BucketDictItemIteratorImplementation(BucketDictIteratorImplementation):
    def get_result(self, node):
        return self.space.newtuple([node.w_key, node.w_value])
