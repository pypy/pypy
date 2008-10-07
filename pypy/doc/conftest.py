import py
from py.__.doc.conftest import Directory, DoctestText, DocfileTests

thisdir = py.magic.autopath().dirpath()

Option = py.test.config.Option
option = py.test.config.addoptions("pypy-doc options", 
        Option('--generate-redirections', action="store_true",
               dest="generateredirections",
               default=True, help="Generate the redirecting HTML files"),
        Option('--enable-doctests', action="store_true",
               dest="doctests", 
               default=False, help="enable doctests in .txt files"), 
    )

class PyPyDoctestText(DoctestText): 
    def runtest(self):
        if not option.doctests: 
            py.test.skip("specify --enable-doctests to run doctests") 
        super(PyPyDoctestText, self).runtest()

    def getcontent(self):
        # XXX execute PyPy prompts as well 
        #     but for now just get rid of those lines
        l = []
        for line in super(PyPyDoctestText, self).getcontent().split('\n'):
            if line.find('>>>>') != -1: 
                line = "" 
            l.append(line) 
        return "\n".join(l) 

class PyPyDocfileTests(DocfileTests):
    DoctestText = PyPyDoctestText 
    
class Directory(Directory): 
    DocfileTests = PyPyDocfileTests
    def recfilter(self, path):
        if path.basename == "statistic":
            return False
        return super(Directory, self).recfilter(path)

try:
    from docutils.parsers.rst import directives, states, roles
    from py.__.rest.directive import register_linkrole
except ImportError:
    pass
else:
    # enable :config: link role
    def config_role(name, rawtext, text, lineno, inliner, options={},
                    content=[]):
        from docutils import nodes
        from pypy.config.pypyoption import get_pypy_config
        from pypy.config.makerestdoc import get_cmdline
        txt = thisdir.join("config", text + ".txt")
        html = thisdir.join("config", text + ".html")
        assert txt.check()
        assert name == "config"
        sourcedir = py.path.local(inliner.document.settings._source).dirpath()
        curr = sourcedir
        prefix = ""
        while 1:
            relative = str(html.relto(curr))
            if relative:
                break
            curr = curr.dirpath()
            prefix += "../"
        config = get_pypy_config()
        # begin horror
        h, n = config._cfgimpl_get_home_by_path(text)
        opt = getattr(h._cfgimpl_descr, n)
        # end horror
        cmdline = get_cmdline(opt.cmdline, text)
        if cmdline is not None:
            shortest_long_option = 'X'*1000
            for cmd in cmdline.split():
                if cmd.startswith('--') and len(cmd) < len(shortest_long_option):
                    shortest_long_option = cmd
            text = shortest_long_option
        target = prefix + relative
        print text, target
        reference_node = nodes.reference(rawtext, text, name=text, refuri=target)
        return [reference_node], []
    config_role.content = True
    config_role.options = {}
    roles.register_canonical_role("config", config_role)
