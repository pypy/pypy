
class Config(object):
    """main config

        there's 3 levels of configuration values: default ones, stuff from
        config files and command-line options, all cascading
        
        config is divided in groups, each group is an instance on the root
        (this object)
    """
    _frozen = False
    
    def __init__(self, descr, **overrides):
        self._descr = descr
        self._value_owners = {}
        self._build(overrides)

    def _build(self, overrides):
        for child in self._descr._children:
            if isinstance(child, Option):
                self.__dict__[child._name] = child.default
                self._value_owners[child._name] = 'default'
            elif isinstance(child, OptionDescription):
                self.__dict__[child._name] = Config(child)
        for name, value in overrides.iteritems():
            setattr(self, name, value)

    def __setattr__(self, name, value):
        if self._frozen:
            raise TypeError("trying to change a frozen option object")
        if name.startswith('_'):
            self.__dict__[name] = value
            return
        self.setoption(name, value, 'user')

    def setoption(self, name, value, who):
        if name not in self.__dict__:
            raise ValueError('unknown option %s' % (name,))
        child = getattr(self._descr, name)
        oldowner = self._value_owners[child._name]
        oldvalue = getattr(self, name)
        if oldowner == 'required':
            if oldvalue != value:
                raise ValueError('can not override value %s for option %s' %
                                    (value, name))
            return
        child.setoption(self, value)
        self._value_owners[name] = who

    def require(self, name, value):
        self.setoption(name, value, "required")

    def _get_by_path(self, path):
        """returns tuple (config, name)"""
        path = path.split('.')
        for step in path[:-1]:
            self = getattr(self, step)
        return self, path[-1]

    def _freeze_(self):
        self._frozen = True
        return True

    def getkey(self):
        return self._descr.getkey(self)

    def __hash__(self):
        return hash(self.getkey())

    def __eq__(self, other):
        return self.getkey() == other.getkey()

    def __ne__(self, other):
        return not self == other

    def __iter__(self):
        for child in self._descr._children:
            if isinstance(child, Option):
                yield child._name, getattr(self, child._name)

class Option(object):
    def validate(self, value):
        raise NotImplementedError('abstract base class')

    def getdefault(self):
        return self.default

    def setoption(self, config, value):
        name = self._name
        if not self.validate(value):
            raise ValueError('invalid value %s for option %s' % (value, name))
        config.__dict__[name] = value

    def getkey(self, value):
        return value

class ChoiceOption(Option):
    def __init__(self, name, doc, values, default):
        self._name = name
        self.doc = doc
        self.values = values
        self.default = default

    def validate(self, value):
        return value in self.values

class BoolOption(ChoiceOption):
    def __init__(self, name, doc, default=True, requires=None):
        super(BoolOption, self).__init__(name, doc, [True, False], default)
        self._requires = requires or []

    def setoption(self, config, value):
        name = self._name
        for path, reqvalue in self._requires:
            subconfig, name = config._get_by_path(path)
            subconfig.require(name, reqvalue)
        super(BoolOption, self).setoption(config, value)

class IntOption(Option):
    def __init__(self, name, doc, default=True):
        self._name = name
        self.doc = doc
        self.default = default

    def validate(self, value):
        try:
            int(value)
        except TypeError:
            return False
        return True

    def setoption(self, config, value):
        super(IntOption, self).setoption(config, int(value))


class IntOption(Option):
    def __init__(self, name, doc, default=0):
        self._name = name
        self.doc = doc
        self.default = default

    def validate(self, value):
        try:
            int(value)
        except TypeError:
            return False
        return True

    def setoption(self, config, value):
        try:
            super(IntOption, self).setoption(config, int(value))
        except TypeError, e:
            raise ValueError(*e.args)


class FloatOption(Option):
    def __init__(self, name, doc, default=0.0):
        self._name = name
        self.doc = doc
        self.default = default

    def validate(self, value):
        try:
            float(value)
        except TypeError:
            return False
        return True

    def setoption(self, config, value):
        try:
            super(FloatOption, self).setoption(config, float(value))
        except TypeError, e:
            raise ValueError(*e.args)


class OptionDescription(object):
    def __init__(self, name, children):
        self._name = name
        self._children = children
        self._build()

    def _build(self):
        for child in self._children:
            setattr(self, child._name, child)

    def getkey(self, config):
        return tuple([child.getkey(getattr(config, child._name))
                      for child in self._children])
