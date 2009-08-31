from pypy.objspace.std.listmultiobject import ListImplementation


class ViewListImplementation(ListImplementation):

    def __init__(self, space, context, getitem, setitem, delitem, append,
                 length):
        self.space = space
        self.context = context
        self.getitem_hook = getitem
        self.setitem_hook = setitem
        self.delitem_hook = delitem
        self.append_hook = append
        self.length_hook = length

    def getitem(self, i):
        return self.getitem_hook(self.space, self.context, i)

    def getitem_slice(self, start, stop):
        return [self.getitem(i) for i in range(start, stop)]

    def setitem(self, i, w_something):
        self.setitem_hook(self.space, self.context, i, w_something)
        return self

    def delitem(self, i):
        self.delitem_hook(self.space, self.context, i)
        return self

    def delitem_slice(self, start, stop):
        for i in range(start, stop):
            self.delitem(i)
        return self

    def append(self, w_something):
        self.append_hook(self.space, self.context, w_something)
        return self

    def extend(self, other):
        for w_something in other.get_list_w():
            self.append(w_something)
        return self

    def length(self):
        return self.length_hook(self.space, self.context)

    def get_list_w(self):
        return [self.getitem(i) for i in range(self.length())]
