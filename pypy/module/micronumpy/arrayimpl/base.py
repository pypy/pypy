
class BaseArrayImplementation(object):
    pass

class BaseArrayIterator(object):
    def next(self):
        raise NotImplementedError # purely abstract base class

    def setitem(self, elem):
        raise NotImplementedError
