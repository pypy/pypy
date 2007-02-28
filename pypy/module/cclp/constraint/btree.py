from pypy.interpreter import baseobjspace

class Found(Exception): pass

class BTree(object):
    """binary tree"""

    def __init__(self):
        self.leaf = True

    def _populate(self, key, val):
        self.leaf = False
        self.key = key
        self.val = val
        self.left = BTree()
        self.right = BTree()

    def add(self, key, val):
        assert isinstance(key, int)
        assert isinstance(val, baseobjspace.W_Root)
        if self.leaf:
            self._populate(key, val)
        else:
            if key > self.key:
                self.right.add(key, val)
            else:
                self.left.add(key, val)

    def _in(self, key):
        if self.leaf:
            return False
        if self.key == key: raise Found
        self.left._in(key)
        self.right._in(key)

    def __contains__(self, key):
        if self.leaf: return False
        if self.key == key: return True
        try:
            self._in(key)
            self._in(key)
            return False
        except Found:
            return True

    def _infixly(self, output, ret=0):
        """depending on the value of ret:
           0 : keys
           1 : values
           2 : both (items)
        """
        if self.leaf: return
        self.left._infixly(output, ret)
        if ret == 0:
            output.append(self.key)
        elif ret == 1:
            output.append(self.val)
        else:
            output.append((self.key, self.val))
        self.right._infixly(output, ret)

    def keys(self):
        out = []
        self._infixly(out, ret=0)
        return out

    def values(self):
        out = []
        self._infixly(out, ret=1)
        return out

    def items(self):
        out = []
        self._infixly(out, ret=2)
        return out
