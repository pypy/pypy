

class ClassType(object):
    __slots__ = ['....']

    def __init__(self, name, bases, dict):
        self.__name__ = name
        self.__bases__ = bases
        self.__dict__ = dict

    def __getattr__(self, attr):
        try:
            return self.__dict__[attr]
        except KeyError:
            raise AttributeError, "Class %s has no attribute %s" % (
                self.__name__, attr)
