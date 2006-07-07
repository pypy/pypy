class Config(object):
    """main config

        there's 3 levels of configuration values: default ones, stuff from
        config files and command-line options, all cascading
        
        config is divided in groups, each group is an instance on the root
        (this object)
    """
    
    def __init__(self, descr):
        self._descr = descr
        self._build()

    def _build(self):
        for child in self._descr._children:
            if isinstance(child, Option):
                self.__dict__[child._name] = child.default
            elif isinstance(child, OptionDescription):
                self.__dict__[child._name] = Config(child)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            self.__dict__[name] = value
            return
        if name not in self.__dict__:
            raise ValueError('unknown option %s' % (name,))
        child = getattr(self._descr, name)
        if not child.validate(value):
            raise ValueError('invalid value %s for option %s' % (value, name))
        self.__dict__[name] = value

    def _freeze_(self):
        return True
        
class Option(object):
    def __init__(self, name, doc, values, default):
        self._name = name
        self.doc = doc
        self.values = values
        self.default = default

    def validate(self, value):
        return value in self.values

class OptionDescription(object):
    def __init__(self, name, children):
        self._name = name
        self._children = children
        self._build()

    def _build(self):
        for child in self._children:
            setattr(self, child._name, child)
