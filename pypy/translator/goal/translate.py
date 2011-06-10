#! /usr/bin/env pypy
"""
Command-line options for translate:

    See below
"""
import sys, os, new

import autopath 
import py
# clean up early pypy/_cache
try:
    py.path.local(autopath.pypydir).join('_cache').remove()
except Exception:
    pass

from pypy.config.config import to_optparse, OptionDescription, BoolOption, \
                               ArbitraryOption, StrOption, IntOption, Config, \
                               ChoiceOption, OptHelpFormatter
from pypy.config.translationoption import get_combined_translation_config
from pypy.config.translationoption import set_opt_level, final_check_config
from pypy.config.translationoption import OPT_LEVELS, DEFAULT_OPT_LEVEL
from pypy.config.translationoption import PLATFORMS, set_platform


GOALS= [
        ("annotate", "do type inference", "-a --annotate", ""),
        ("rtype", "do rtyping", "-t --rtype", ""),
        ("pyjitpl", "JIT generation step", "--pyjitpl", ""),
        ("jittest", "JIT test with llgraph backend", "--jittest", ""),
        ("backendopt", "do backend optimizations", "--backendopt", ""),
        ("source", "create source", "-s --source", ""),
        ("compile", "compile", "-c --compile", " (default goal)"),
        ("run", "run the resulting binary", "--run", ""),
        ("llinterpret", "interpret the rtyped flow graphs", "--llinterpret", ""),
       ]
def goal_options():
    result = []
    for name, doc, cmdline, extra in GOALS:
        optional = False
        if name.startswith('?'):
            optional = True
            name = name[1:]
        yesdoc = doc[0].upper()+doc[1:]+extra
        result.append(BoolOption(name, yesdoc, default=False, cmdline=cmdline,
                                 negation=False))
        if not optional:
            result.append(BoolOption("no_%s" % name, "Don't "+doc, default=False,
                                     cmdline="--no-"+name, negation=False))
    return result

translate_optiondescr = OptionDescription("translate", "XXX", [
    StrOption("targetspec", "XXX", default='targetpypystandalone',
              cmdline=None),
    ChoiceOption("opt",
                 "optimization level", OPT_LEVELS, default=DEFAULT_OPT_LEVEL,
                 cmdline="--opt -O"),
    BoolOption("profile",
               "cProfile (to debug the speed of the translation process)",
               default=False,
               cmdline="--profile"),
    BoolOption("pdb",
               "Always run pdb even if the translation succeeds",
               default=False,
               cmdline="--pdb"),
    BoolOption("batch", "Don't run interactive helpers", default=False,
               cmdline="--batch", negation=False),
    IntOption("huge", "Threshold in the number of functions after which "
                      "a local call graph and not a full one is displayed",
              default=100, cmdline="--huge"),
    BoolOption("view", "Start the pygame viewer", default=False,
               cmdline="--view", negation=False),
    BoolOption("help", "show this help message and exit", default=False,
               cmdline="-h --help", negation=False),
    BoolOption("fullhelp", "show full help message and exit", default=False,
               cmdline="--full-help", negation=False),
    ArbitraryOption("goals", "XXX",
                    defaultfactory=list),
    # xxx default goals ['annotate', 'rtype', 'backendopt', 'source', 'compile']
    ArbitraryOption("skipped_goals", "XXX",
                    defaultfactory=lambda: ['run']),
    OptionDescription("goal_options",
                      "Goals that should be reached during translation", 
                      goal_options()),        
])

    
OVERRIDES = {
    'translation.debug': False,
}

import optparse
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("translation")
py.log.setconsumer("translation", ansi_log)

def load_target(targetspec):
    log.info("Translating target as defined by %s" % targetspec)
    if not targetspec.endswith('.py'):
        targetspec += '.py'
    thismod = sys.modules[__name__]
    sys.modules['translate'] = thismod
    specname = os.path.splitext(os.path.basename(targetspec))[0]
    sys.path.insert(0, os.path.dirname(targetspec))
    mod = __import__(specname)
    return mod.__dict__

def parse_options_and_load_target():
    opt_parser = optparse.OptionParser(usage="%prog [options] [target] [target-specific-options]",
                                       prog="translate",
                                       formatter=OptHelpFormatter(),
                                       add_help_option=False)

    opt_parser.disable_interspersed_args()

    config = get_combined_translation_config(
                overrides=OVERRIDES, translating=True)
    to_optparse(config, parser=opt_parser, useoptions=['translation.*'])
    translateconfig = Config(translate_optiondescr)
    to_optparse(translateconfig, parser=opt_parser)

    options, args = opt_parser.parse_args()

    # set goals and skipped_goals
    reset = False
    for name, _, _, _ in GOALS:
        if name.startswith('?'):
            continue
        if getattr(translateconfig.goal_options, name):
            if name not in translateconfig.goals:
                translateconfig.goals.append(name)
        if getattr(translateconfig.goal_options, 'no_'+name):
            if name not in translateconfig.skipped_goals:
                if not reset:
                    translateconfig.skipped_goals[:] = []
                    reset = True
                translateconfig.skipped_goals.append(name)
        
    if args:
        arg = args[0]
        args = args[1:]
        if os.path.isfile(arg+'.py'):
            assert not os.path.isfile(arg), (
                "ambiguous file naming, please rename %s" % arg)
            translateconfig.targetspec = arg
        elif os.path.isfile(arg) and arg.endswith('.py'):
            translateconfig.targetspec = arg[:-3]
        else:
            log.ERROR("Could not find target %r" % (arg, ))
            sys.exit(1)

    # apply the platform settings
    set_platform(config)

    targetspec = translateconfig.targetspec
    targetspec_dic = load_target(targetspec)

    if args and not targetspec_dic.get('take_options', False):
        log.WARNING("target specific arguments supplied but will be ignored: %s" % ' '.join(args))

    # give the target the possibility to get its own configuration options
    # into the config
    if 'get_additional_config_options' in targetspec_dic:
        optiondescr = targetspec_dic['get_additional_config_options']()
        config = get_combined_translation_config(
                optiondescr,
                existing_config=config,
                translating=True)

    # apply the optimization level settings
    set_opt_level(config, translateconfig.opt)

    # let the target modify or prepare itself
    # based on the config
    if 'handle_config' in targetspec_dic:
        targetspec_dic['handle_config'](config, translateconfig)

    # perform checks (if any) on the final config
    final_check_config(config)

    if translateconfig.help:
        opt_parser.print_help()
        if 'print_help' in targetspec_dic:
            print "\n\nTarget specific help:\n\n"
            targetspec_dic['print_help'](config)
        print "\n\nFor detailed descriptions of the command line options see"
        print "http://codespeak.net/pypy/dist/pypy/doc/config/commandline.html"
        sys.exit(0)
    
    return targetspec_dic, translateconfig, config, args

def log_options(options, header="options in effect"):
    # list options (xxx filter, filter for target)
    log('%s:' % header)
    optnames = options.__dict__.keys()
    optnames.sort()
    for name in optnames:
        optvalue = getattr(options, name)
        log('%25s: %s' %(name, optvalue))
   
def log_config(config, header="config used"):
    log('%s:' % header)
    log(str(config))
    for warning in config.get_warnings():
        log.WARNING(warning)

def main():
    targetspec_dic, translateconfig, config, args = parse_options_and_load_target()
    from pypy.translator import translator
    from pypy.translator import driver
    from pypy.translator.tool.pdbplus import PdbPlusShow

    if translateconfig.view:
        translateconfig.pdb = True

    if translateconfig.profile:
        from cProfile import Profile
        prof = Profile()
        prof.enable()
    else:
        prof = None

    t = translator.TranslationContext(config=config)

    pdb_plus_show = PdbPlusShow(t) # need a translator to support extended commands

    def finish_profiling():
        if prof:
            prof.disable()
            statfilename = 'prof.dump'
            log.info('Dumping profiler stats to: %s' % statfilename)
            prof.dump_stats(statfilename)        

    def debug(got_error):
        tb = None
        if got_error:
            import traceback
            errmsg = ["Error:\n"]
            exc, val, tb = sys.exc_info()
            errmsg.extend([" %s" % line for line in traceback.format_exception(exc, val, tb)])
            block = getattr(val, '__annotator_block', None)
            if block:
                class FileLike:
                    def write(self, s):
                        errmsg.append(" %s" % s)
                errmsg.append("Processing block:\n")
                t.about(block, FileLike())
            log.ERROR(''.join(errmsg))
        else:
            log.event('Done.')

        if translateconfig.batch:
            log.event("batch mode, not calling interactive helpers")
            return
        
        log.event("start debugger...")

        if translateconfig.view:
            try:
                t1 = drv.hint_translator
            except (NameError, AttributeError):
                t1 = t
            from pypy.translator.tool import graphpage
            page = graphpage.TranslatorPage(t1, translateconfig.huge)
            page.display_background()

        pdb_plus_show.start(tb)

    try:
        drv = driver.TranslationDriver.from_targetspec(targetspec_dic, config, args,
                                                       empty_translator=t,
                                                       disable=translateconfig.skipped_goals,
                                                       default_goal='compile')
        log_config(translateconfig, "translate.py configuration")
        if config.translation.jit:
            if 'jitpolicy' not in targetspec_dic:
                raise Exception('target has no jitpolicy defined.')
            if (translateconfig.goals != ['annotate'] and
                translateconfig.goals != ['rtype']):
                drv.set_extra_goals(['pyjitpl'])
            # early check:
            from pypy.jit.backend.detect_cpu import getcpuclassname
            getcpuclassname(config.translation.jit_backend)

        log_config(config.translation, "translation configuration")
        pdb_plus_show.expose({'drv': drv, 'prof': prof})

        if config.translation.output:
            drv.exe_name = config.translation.output
        elif drv.exe_name is None and '__name__' in targetspec_dic:
            drv.exe_name = targetspec_dic['__name__'] + '-%(backend)s'

        # Double check to ensure we are not overwriting the current interpreter
        try:
            this_exe = py.path.local(sys.executable).new(ext='')
            exe_name = drv.compute_exe_name()
            samefile = this_exe.samefile(exe_name)
            assert not samefile, (
                'Output file %s is the currently running '
                'interpreter (use --output=...)'% exe_name)
        except EnvironmentError:
            pass

        goals = translateconfig.goals
        try:
            drv.proceed(goals)
        finally:
            drv.timer.pprint()
    except SystemExit:
        raise
    except:
        finish_profiling()
        debug(True)
        raise SystemExit(1)
    else:
        finish_profiling()
        if translateconfig.pdb:
            debug(False)


if __name__ == '__main__':
    main()
