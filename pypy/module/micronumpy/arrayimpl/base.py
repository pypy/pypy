
class BaseArrayImplementation(object):
    is_scalar = False

class BaseArrayIterator(object):
    def next(self):
        raise NotImplementedError # purely abstract base class

    def setitem(self, elem):
        raise NotImplementedError

    def set_scalar_object(self, value):
        raise NotImplementedError # works only on scalars
