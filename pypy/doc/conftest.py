import py
from py.__.doc.conftest import Directory, DoctestText, ReSTChecker
from py.__.rest.directive import register_linkrole

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

    def run(self): 
        if not option.doctests: 
            py.test.skip("specify --enable-doctests to run doctests") 
        # XXX refine doctest support with respect to scoping 
        return super(PyPyDoctestText, self).run()
        
    def execute(self, module, docstring): 
        # XXX execute PyPy prompts as well 
        l = []
        for line in docstring.split('\n'): 
            if line.find('>>>>') != -1: 
                line = "" 
            l.append(line) 
        text = "\n".join(l) 
        super(PyPyDoctestText, self).execute(module, text) 

        #mod = py.std.types.ModuleType(self.fspath.basename, text) 
        #self.mergescopes(mod, scopes) 
        #failed, tot = py.std.doctest.testmod(mod, verbose=1)
        #if failed:
        #    py.test.fail("doctest %s: %s failed out of %s" %(
        #                 self.fspath, failed, tot))

class PyPyReSTChecker(ReSTChecker): 
    DoctestText = PyPyDoctestText 
    
class Directory(Directory): 
    ReSTChecker = PyPyReSTChecker 
    def run(self):
        l = super(Directory, self).run()
        if 'statistic' in l:
            l.remove('statistic')
        return l

try:
    from docutils.parsers.rst import directives, states, roles
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
