import subprocess
from pypy.translator.c.test.test_standalone import TestStandalone as CTestStandalone
from pypy.annotation.listdef import s_list_of_strings
from pypy.translator.translator import TranslationContext
from pypy.translator.cli.sdk import SDK

class CliStandaloneBuilder(object):

    def __init__(self, translator, entry_point, config):
        self.translator = translator
        self.entry_point = entry_point
        self.config = config
        self.exe_name = None

    def compile(self):
        from pypy.translator.cli.test.runtest import _build_gen_from_graph
        graph = self.translator.graphs[0]
        gen = _build_gen_from_graph(graph, self.translator, standalone=True)
        gen.generate_source()
        self.exe_name = gen.build_exe()

    def cmdexec(self, args='', env=None, err=False):
        assert self.exe_name
        stdout, stderr, retval = self.run(args, env=env)
        if retval != 0:
            raise Exception("Returned %d" % (retval,))
        if err:
            return stdout, stderr
        return stdout

    def run(self, args, env):
        arglist = SDK.runtime() + [self.exe_name] + map(str, args)
        env = env.copy()
        env['LANG'] = 'C'
        mono = subprocess.Popen(arglist, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env)
        stdout, stderr = mono.communicate()
        retval = mono.wait()
        return stdout, stderr, retval


class TestStandalone(object):
    config = None

    def compile(self, entry_point):
        t = TranslationContext(self.config)
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper(type_system='ootype').specialize()

        cbuilder = CliStandaloneBuilder(t, entry_point, t.config)
        cbuilder.compile()
        return t, cbuilder

    test_debug_print_start_stop = CTestStandalone.test_debug_print_start_stop.im_func
