"""
A minimalist binary tree implementation
whose values are (descendants of) BTreeNodes.
This alleviates some typing difficulties when
using TimSort on lists of the form [(key, Thing), ...]
"""

class BTreeNode:

    def __init__(self, key):
        self.key = key
        self.left = None
        self.right = None

    def add(self, val):
        key = val.key
        assert isinstance(key, int)
        assert isinstance(val, BTreeNode)
        
        if key > self.key:
            if self.right:
                self.right.add(val)
            else:
                self.right = val
        else:
            if self.left:
                self.left.add(val)
            else:
                self.left = val


    def _values(self, dest):
        if self.left:
            self.left._values(dest)
        dest.append(self)
        if self.right:
            self.right._values(dest)

    def get_values(self):
        dest = []
        self._values( dest )
        return dest

