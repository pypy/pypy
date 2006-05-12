import types
class StaticMethods(type):
    """
    Metaclass that turns plain methods into staticmethods.
    """
    def __new__(cls, cls_name, bases, cls_dict):
        for key, value in cls_dict.iteritems():
            if isinstance(value, types.FunctionType):
                cls_dict[key] = staticmethod(value)
        return type.__new__(cls, cls_name, bases, cls_dict)
