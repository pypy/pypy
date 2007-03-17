import autopath
from pypy.config.pypyoption import get_pypy_config
from pypy.translator.goal import translate
from pypy.translator.goal import targetpypystandalone
from pypy.translator.driver import TranslationDriver
import os, sys, traceback, random

def longoptfromname(config, name):
    from pypy.config.makerestdoc import get_cmdline
    # begin horror
    h, n = config._cfgimpl_get_home_by_path(name)
    opt = getattr(h._cfgimpl_descr, n)
    # end horror
    cmdline = get_cmdline(opt.cmdline, name)
    assert cmdline is not None
    shortest_long_option = 'X'*1000
    for cmd in cmdline.split():
        if cmd.startswith('--') and len(cmd) < len(shortest_long_option):
            shortest_long_option = cmd
    return shortest_long_option

def exe_name_from_options(config, opts):
    from pypy.module.sys.version import svn_revision

    backend = config.translation.backend
    if not backend:
        backend = 'c'
    rev = svn_revision()

    nameparts = []

    for opt, v in opts.iteritems():
        if opt == 'translation.backend':
            backend = v
        optname = longoptfromname(config, opt).strip('-')
        if v is False:
            optname = 'no-' + optname
        elif v is not True:
            optname += '=' + str(v)
        nameparts.append(optname)

    suffix = ''
    if nameparts:
        def k(s):
            if s.startswith('no-'):
                return s[3:]
            else:
                return s
        nameparts.sort(key=k)
        suffix = '-' + '-'.join(nameparts)

    return 'pypy-%s-%d%s'%(backend, rev, suffix)

def _build(config, exe_name):
    driver = TranslationDriver.from_targetspec(
        targetpypystandalone.__dict__,
        config=config)
    driver.exe_name = exe_name
    driver.compile()

def build_pypy_with_options(basedir, opts):
    config = get_pypy_config(translate.OVERRIDES, translating=True)

    try:
        config.set(**opts)
    except:
        return exe_name_from_options(config, opts), "didn't configure"

    exe_name = os.path.join(basedir, exe_name_from_options(config, opts))

    print exe_name,
    sys.stdout.flush()

    pid = os.fork()

    if pid == 0:
        logfile = open(exe_name + '-log', 'w')
        davenull = os.open('/dev/null', os.O_RDONLY)
        os.dup2(davenull, 0)
        os.dup2(logfile.fileno(), 1)
        os.dup2(logfile.fileno(), 2)
        try:
            try:
                r = _build(config, exe_name)
            finally:
                logfile.close()
        except:
            os._exit(1)
        else:
            os._exit(0)
    else:
        pid, status = os.waitpid(pid, 0)
        if status:
            r = 'failed'
        else:
            r = 'succeeded'
        print r
        return exe_name, r

def get_options(fname):
    def gen_opts(sofar, remaining):
        if not remaining:
            yield sofar
        else:
            for (k, v) in remaining[0]:
                d2 = sofar.copy()
                d2[k] = v
                for d in gen_opts(d2, remaining[1:]):
                    yield d
    options = []
    for line in open(fname):
        l = []
        optname, options_ = line.split(':')
        options.append([(optname.strip(), eval(optval.strip())) for optval in options_.split(',')])
    return gen_opts({}, options)


if __name__ == '__main__':
    basedir = sys.argv[1]
    optionsfile = sys.argv[2]
    results = []
    options = list(get_options(optionsfile))
    random.shuffle(options)
    for opts in options:
        results.append(build_pypy_with_options(basedir, opts))
    out = open(os.path.join(basedir, 'results'), 'w')
    for exe, r in results:
        print >>out, exe, r
