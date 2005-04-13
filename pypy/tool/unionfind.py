
# union-find impl, a info object is attached to the roots

class UnionFind(object):

    def __init__(self, info_factory):
        self.link_to_parent = {}
        self.weight = {}
        self.info_factory = info_factory
        self.root_info = {}

    # mapping-like [] access
    def __getitem__(self, obj):
        if obj not in self.link_to_parent:
            raise KeyError, obj

        ignore, rep, access = self.find(obj)

        return access

    def find(self, obj):  # -> new_root, obj, info
        if obj not in self.link_to_parent:
            info = self.root_info[obj] = self.info_factory(obj)
            self.weight[obj] = 1
            self.link_to_parent[obj] = obj
            return True, obj, info

        to_root = [obj]
        parent = self.link_to_parent[obj]
        while parent is not to_root[-1]:
            to_root.append(parent)
            parent = self.link_to_parent[parent]

        for obj in to_root:
            self.link_to_parent[obj] = parent

        return False, parent, self.root_info[parent]


    def union(self, obj1, obj2): # -> not_noop, rep, info

        new1, rep1, info1 = self.find(obj1)
        new2, rep2, info2 = self.find(obj2)

        if rep1 is rep2:
            return new1 or new2, rep1, info1

        w1 = self.weight[rep1]
        w2 = self.weight[rep2]

        w = w1 + w2

        if w1 < w2:
            rep1, rep2, info1, info2, = rep2, rep1, info2, info1

        info1.update(info2)

        self.link_to_parent[rep2] = rep1

        del self.weight[rep2]
        del self.root_info[rep2]

        self.weight[rep1] = w
        self.root_info[rep1] = info1

        return True, rep1, info1
        

    
