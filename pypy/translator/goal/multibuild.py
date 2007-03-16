from pypy.config.pypyoption import get_pypy_config
from pypy.translator.goal import translate
from pypy.translator.goal import targetpypystandalone
from pypy.translator.driver import TranslationDriver
import os, sys, traceback

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
            continue
        optname = longoptfromname(config, opt).strip('-')
        if v is False:
            optname = 'no-' + optname
        elif v is not True:
            optname += '=' + str(v)
        nameparts.append(optname)

    suffix = ''
    if nameparts:
        nameparts.sort()
        suffix = '-' + '-'.join(nameparts)

    return 'pypy-%s-%d%s'%(backend, rev, suffix)

def build_pypy_with_options(basedir, opts):
    config = get_pypy_config(translate.OVERRIDES, translating=True)

    try:
        config.set(**opts)
    except:
        return "didn't configure"

    driver = TranslationDriver.from_targetspec(
        targetpypystandalone.__dict__,
        config=config)
    driver.exe_name = os.path.join(basedir, exe_name_from_options(config, opts))
    se = sys.stderr
    so = sys.stdout
    try:
        sys.stderr = sys.stdout = open(driver.exe_name + '-log', 'w')
        try:
            driver.compile()
        except (SystemExit, KeyboardInterrupt):
            traceback.print_exc()
            raise
        except:
            traceback.print_exc()
            return "failed"
        else:
            return "worked"
    finally:
        sys.stderr = se
        sys.stdout = so

print build_pypy_with_options('', {'translation.stackless':True})
