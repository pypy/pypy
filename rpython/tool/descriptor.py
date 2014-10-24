import sys, types

class InstanceMethod(object):
    "Like types.InstanceMethod, but with a reasonable (structural) equality."

    def __init__(self, im_func, im_self, im_class):
        self.im_func = im_func
        self.im_self = im_self
        self.im_class = im_class

    def __call__(self, *args, **kwds):
        firstarg = self.im_self
        if firstarg is None:
            if not args or not isinstance(args[0], self.im_class):
                raise TypeError(
                    "must be called with %r instance as first argument" % (
                    self.im_class,))
            firstarg = args[0]
            args = args[1:]
        return self.im_func(firstarg, *args, **kwds)

    def __eq__(self, other):
        return isinstance(other, InstanceMethod) and (
            self.im_func == other.im_func and
            self.im_self == other.im_self)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.im_func, self.im_self))

if '__pypy__' in sys.modules:
    def normalize_method(method):
        '''Turn everything that behaves like a method into an InstanceMethod object'''
        if isinstance(method, types.MethodType):
            return InstanceMethod(method.__func__, method.__self__, method.im_class)
        else:
            raise ValueError('Not a method')

else:
    slot_wrapper = type(object.__init__)
    method_wrapper = type(object().__init__)
    method_descriptor = type(str.join)

    def normalize_method(method):
        '''Turn everything that behaves like a method into an InstanceMethod object'''
        if isinstance(method, types.MethodType):
            return InstanceMethod(method.__func__, method.__self__, method.im_class)
        elif isinstance(method, types.BuiltinMethodType):
            im_self = method.__self__
            desc = getattr(type(im_self), method.__name__)
            return InstanceMethod(desc, im_self, type(im_self))
        elif isinstance(method, slot_wrapper):
            baseslot = getattr(method.__objclass__, method.__name__)
            cls = method.__objclass__
            return InstanceMethod(baseslot, None, baseslot.__objclass__)
        elif isinstance(method, method_wrapper):
            slot = getattr(method.__objclass__, method.__name__)
            return InstanceMethod(slot, method.__self__, slot.__objclass__)
        elif isinstance(method, method_descriptor):
            cls = method.__objclass__
            return InstanceMethod(method, None, method.__objclass__)
        else:
            raise ValueError('Not a method')


