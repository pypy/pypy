
class BaseArrayImplementation(object):
    def is_scalar(self):
        return False

    def base(self):
        raise NotImplementedError

    def create_iter(self, shape=None, backward_broadcast=False, require_index=False):
        raise NotImplementedError

class BaseArrayIterator(object):
    def next(self):
        raise NotImplementedError # purely abstract base class

    def setitem(self, elem):
        raise NotImplementedError

    def set_scalar_object(self, value):
        raise NotImplementedError # works only on scalars
