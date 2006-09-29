
from py.compat import optparse

class Config(object):
    _frozen = False
    
    def __init__(self, descr, parent=None, **overrides):
        self._descr = descr
        self._value_owners = {}
        self._parent = parent
        self._build(overrides)

    def _build(self, overrides):
        for child in self._descr._children:
            if isinstance(child, Option):
                self.__dict__[child._name] = child.default
                self._value_owners[child._name] = 'default'
            elif isinstance(child, OptionDescription):
                self.__dict__[child._name] = Config(child, parent=self)
        for name, value in overrides.iteritems():
            subconfig, name = self._get_by_path(name)
            setattr(subconfig, name, value)

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

    def _get_toplevel(self):
        while self._parent is not None:
            self = self._parent
        return self

    def _freeze_(self):
        self.__dict__['_frozen'] = True
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

    def __str__(self):
        result = "[%s]\n" % (self._descr._name, )
        for child in self._descr._children:
            if isinstance(child, Option):
                if self._value_owners[child._name] == 'default':
                    continue
                result += "    %s = %s\n" % (
                    child._name, getattr(self, child._name))
            else:
                substr = str(getattr(self, child._name))
                substr = "    " + substr[:-1].replace("\n", "\n    ") + "\n"
                result += substr
        return result

    def getpaths(self, include_groups=False, currpath=None):
        """returns a list of all paths in self, recursively
        
            currpath should not be provided (helps with recursion)
        """
        if currpath is None:
            currpath = []
        paths = []
        for option in self._descr._children:
            attr = option._name
            if attr.startswith('_'):
                continue
            value = getattr(self, attr)
            if isinstance(value, Config):
                if include_groups:
                    paths.append('.'.join(currpath + [attr]))
                currpath.append(attr)
                paths += value.getpaths(include_groups=include_groups,
                                        currpath=currpath)
                currpath.pop()
            else:
                paths.append('.'.join(currpath + [attr]))
        return paths


DEFAULT_OPTION_NAME = object()


class Option(object):
    def __init__(self, name, doc, cmdline=DEFAULT_OPTION_NAME):
        self._name = name
        self.doc = doc
        self.cmdline = cmdline
        
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

    def add_optparse_option(self, argnames, parser, config):
        raise NotImplemented('abstract base class')

class ChoiceOption(Option):
    def __init__(self, name, doc, values, default, requires=None,
                 cmdline=DEFAULT_OPTION_NAME):
        super(ChoiceOption, self).__init__(name, doc, cmdline)
        self.values = values
        self.default = default
        if requires is None:
            requires = {}
        self._requires = requires

    def setoption(self, config, value):
        name = self._name
        for path, reqvalue in self._requires.get(value, []):
            subconfig, name = config._get_toplevel()._get_by_path(path)
            subconfig.require(name, reqvalue)
        super(ChoiceOption, self).setoption(config, value)

    def validate(self, value):
        return value in self.values

    def add_optparse_option(self, argnames, parser, config):
        def _callback(option, opt_str, value, parser, *args, **kwargs):
            try:
                config.setoption(self._name, value.strip(), who='cmdline')
            except ValueError, e:
                raise optparse.OptionValueError(e.args[0])
        parser.add_option(help=self.doc,
                            action='callback', type='string',
                            callback=_callback, *argnames)

class BoolOption(ChoiceOption):
    def __init__(self, name, doc, default=True, requires=None,
                 cmdline=DEFAULT_OPTION_NAME):
        if requires is not None:
            requires = {True: requires}
        super(BoolOption, self).__init__(name, doc, [True, False], default,
                                         requires=requires,
                                         cmdline=cmdline)

    def add_optparse_option(self, argnames, parser, config):
        def _callback(option, opt_str, value, parser, *args, **kwargs):
            try:
                config.setoption(self._name, True, who='cmdline')
            except ValueError, e:
                raise optparse.OptionValueError(e.args[0])
        parser.add_option(help=self.doc,
                            action='callback',
                            callback=_callback, *argnames)

class IntOption(Option):
    def __init__(self, name, doc, default=0, cmdline=DEFAULT_OPTION_NAME):
        super(IntOption, self).__init__(name, doc, cmdline)
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

    def add_optparse_option(self, argnames, parser, config):
        def _callback(option, opt_str, value, parser, *args, **kwargs):
            config.setoption(self._name, value, who='cmdline')
        parser.add_option(help=self.doc,
                            action='callback', type='int',
                            callback=_callback, *argnames)

class FloatOption(Option):
    def __init__(self, name, doc, default=0.0, cmdline=DEFAULT_OPTION_NAME):
        super(FloatOption, self).__init__(name, doc, cmdline)
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

    def add_optparse_option(self, argnames, parser, config):
        def _callback(option, opt_str, value, parser, *args, **kwargs):
            config.setoption(self._name, value, who='cmdline')
        parser.add_option(help=self.doc,
                          action='callback', type='float',
                          callback=_callback, *argnames)

class OptionDescription(object):
    def __init__(self, name, doc, children, cmdline=DEFAULT_OPTION_NAME):
        self._name = name
        self.doc = doc
        self._children = children
        self._build()
        self.cmdline = cmdline

    def _build(self):
        for child in self._children:
            setattr(self, child._name, child)

    def getkey(self, config):
        return tuple([child.getkey(getattr(config, child._name))
                      for child in self._children])

    def add_optparse_option(self, argnames, parser, config):
        for child in self._children:
            if not isinstance(child, BoolOption):
                raise ValueError(
                    "cannot make OptionDescription %s a cmdline option" % (
                        self._name, ))
        def _callback(option, opt_str, value, parser, *args, **kwargs):
            try:
                values = value.split(",")
                for value in values:
                    value = value.strip()
                    option = getattr(self, value, None)
                    if option is None:
                        raise ValueError("did not find option %s" % (value, ))
                    getattr(config, self._name).setoption(
                        value, True, who='cmdline')
            except ValueError, e:
                raise optparse.OptionValueError(e.args[0])
        parser.add_option(help=self._name, action='callback', type='string',
                          callback=_callback, *argnames)


def to_optparse(config, useoptions=None, parser=None):
    grps = {}
    def get_group(name, doc):
        steps = name.split('.')
        if len(steps) < 2:
            return parser
        grpname = steps[-2]
        grp = grps.get(grpname, None)
        if grp is None:
            grp = grps[grpname] = parser.add_option_group(doc)
        return grp

    if parser is None:
        parser = optparse.OptionParser()
    if useoptions is None:
        useoptions = config.getpaths(include_groups=True)
    for path in useoptions:
        if path.endswith(".*"):
            path = path[:-2]
            subconf, name = config._get_by_path(path)
            children = [
                path + "." + child._name
                for child in getattr(subconf, name)._descr._children]
            useoptions.extend(children)
        else:
            subconf, name = config._get_by_path(path)
            option = getattr(subconf._descr, name)
            if option.cmdline is DEFAULT_OPTION_NAME:
                chunks = ('--%s' % (path.replace('.', '-'),),)
            elif option.cmdline is None:
                continue
            else:
                chunks = option.cmdline.split(' ')
            try:
                grp = get_group(path, subconf._descr.doc)
                option.add_optparse_option(chunks, grp, subconf)
            except ValueError:
                # an option group that does not only contain bool values
                pass
    return parser

