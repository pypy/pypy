

class HandleManager:

    def __init__(self, space):
        self.handles_w = [None]
        self.free_list = []

    def new(self, w_object):
        if len(self.free_list) == 0:
            index = len(self.handles_w)
            self.handles_w.append(w_object)
        else:
            index = self.free_list.pop()
            self.handles_w[index] = w_object
        return index

    def close(self, index):
        assert index > 0
        self.handles_w[index] = None
        self.free_list.append(index)

    def consume(self, index):
        """
        Like close, but also return the w_object which was pointed by the handled
        """
        assert index > 0
        w_object = self.handles_w[index]
        self.close(index)
        return w_object

    def dup(self, index):
        w_object = self.handles_w[index]
        return self.new(w_object)


def new(space, w_object):
    mgr = space.fromcache(HandleManager)
    return mgr.new(w_object)

def close(space, index):
    mgr = space.fromcache(HandleManager)
    mgr.close(index)
    
def consume(space, index):
    mgr = space.fromcache(HandleManager)
    return mgr.consume(index)

def dup(space, index):
    mgr = space.fromcache(HandleManager)
    return mgr.dup(index)


class using(object):
    """
    context-manager to new/close a handle
    """

    def __init__(self, space, w_object):
        self.space = space
        self.w_object = w_object
        self.h = -1

    def __enter__(self):
        self.h = new(self.space, self.w_object)
        return self.h

    def __exit__(self, etype, evalue, tb):
        close(self.space, self.h)
