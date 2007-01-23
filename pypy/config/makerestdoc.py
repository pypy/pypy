import py
from py.__.rest.rst import Rest, Paragraph, Strong, ListItem, Title, Link
from py.__.rest.rst import Directive

from pypy.config.config import ChoiceOption, BoolOption, StrOption, IntOption
from pypy.config.config import FloatOption, OptionDescription, Option, Config
from pypy.config.config import DEFAULT_OPTION_NAME

class __extend__(Option):
    def make_rest_doc(self, path=""):
        if path:
            fullpath = "%s.%s" % (path, self._name)
        else:
            fullpath = self._name
        result = Rest(
            Title(fullpath, abovechar="=", belowchar="="),
            Directive("contents"),
            Title("Basic Option Information"),
            ListItem(Strong("name:"), self._name),
            ListItem(Strong("description:"), self.doc))
        if self.cmdline is not None:
            if self.cmdline is DEFAULT_OPTION_NAME:
                cmdline = '--%s' % (fullpath.replace('.', '-'),)
            else:
                cmdline = self.cmdline
            result.add(ListItem(Strong("command-line:"), cmdline))
        return result

class __extend__(ChoiceOption):
    def make_rest_doc(self, path=""):
        content = super(ChoiceOption, self).make_rest_doc(path)
        content.add(ListItem(Strong("option type:"), "choice option"))
        content.add(ListItem(Strong("possible values:"),
                             *[ListItem(str(val)) for val in self.values]))
        if self.default is not None:
            content.add(ListItem(Strong("default:"), str(self.default)))

        requirements = []
        
        for val in self.values:
            if val not in self._requires:
                continue
            req = self._requires[val]
            requirements.append(ListItem("value '%s' requires:" % (val, ),
                *[ListItem(Link(opt, opt + ".html"),
                           "to be set to '%s'" % (rval, ))
                      for (opt, rval) in req]))
        if requirements:
            content.add(ListItem(Strong("requirements:"), *requirements))
        return content

class __extend__(OptionDescription):
    def make_rest_doc(self, path=""):
        if path:
            fullpath = "%s.%s" % (path, self._name)
        else:
            fullpath = self._name
        content = Rest(
            Title(fullpath, abovechar="=", belowchar="="),
            Directive("contents"))
        if path:
            content.add(
                Paragraph(Link("back to parent", path + ".html")))
        for elt in [
            Title("Basic Option Information"),
            ListItem(Strong("name:"), self._name),
            ListItem(Strong("description:"), self.doc),
            Title("Children")
            ]:
            content.add(elt)
        conf = Config(self)
        stack = []
        prefix = fullpath
        curr = content
        for subpath in conf.getpaths(include_groups=True):
            subpath = fullpath + "." + subpath
            while not subpath.startswith(prefix):
                curr, prefix = stack.pop()
            new = curr.add(ListItem(Link(subpath, subpath + ".html")))
            stack.append((curr, prefix))
            prefix = subpath
            curr = new
        return content

