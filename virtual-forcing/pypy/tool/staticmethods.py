import types
class AbstractMethods(type):
    def __new__(cls, cls_name, bases, cls_dict):
        for key, value in cls_dict.iteritems():
            if isinstance(value, types.FunctionType):
                cls_dict[key] = cls.decorator(value)
        return type.__new__(cls, cls_name, bases, cls_dict)


class StaticMethods(AbstractMethods):
    """
    Metaclass that turns plain methods into staticmethods.
    """    
    decorator = staticmethod

class ClassMethods(AbstractMethods):
    """
    Metaclass that turns plain methods into classmethods.
    """    
    decorator = classmethod
