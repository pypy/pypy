
class error(Exception):
    "Usage error of the _continuation module."


from _continuation import flexibleframe


class generator(object):

    def __init__(self, callable):
        self.__func__ = callable

    def __get__(self, obj, type=None):
        return generator(self.__func__.__get__(obj, type))

    def __call__(self, *args, **kwds):
        return genlet(self.__func__, *args, **kwds)


class genlet(flexibleframe):

    def __iter__(self):
        return self

    def next(self, value=None):
        res = self.switch(value)
        if self.is_alive():
            return res
        else:
            raise StopIteration

    send = next
