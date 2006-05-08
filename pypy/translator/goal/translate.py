#! /usr/bin/env python
"""
Command-line options for translate:

    See below
"""
import sys, os

import autopath 


# dict are not ordered, cheat with #_xyz keys and bunchiter
def OPT(*args):
    return args

def bunchiter(d):
    purify = lambda name: name.split('_',1)[1]
    items = d.items()
    items.sort()
    for name, val in items:
        yield purify(name), val

GOAL = object()
SKIP_GOAL = object()

opts = {

    '0_Annotation': {
    '0_annotate': [OPT(('-a', '--annotate'), "Annotate", GOAL),
                 OPT(('--no-annotate',), "Don't annotate", SKIP_GOAL)],
    '1_debug': [OPT(('-d', '--debug'), "Record annotation debug info", True)]
    },

    '1_RTyping': {
    '0_rtype':  [OPT(('-t', '--rtype'), "RType", GOAL),
               OPT(('--no-rtype',), "Don't rtype", SKIP_GOAL)],
    '1_insist': [OPT(('--insist',), "Dont' stop on first rtyper error", True)]
    },
    
    '2_Backend optimisations': {
    '_backendopt':  [OPT(('-o', '--backendopt'), "Do backend optimisations", GOAL),
                 OPT(('--no-backendopt',), "Don't do backend optimisations", SKIP_GOAL)],
    },

    '3_Code generation options': {
    '0_source': [OPT(('-s', '--source'), "Generate source code", GOAL),
               OPT(('--no-source',), "Don't generate source code", SKIP_GOAL)],

    '1_backend': [OPT(('-b', '--backend'), "Backend", ['c', 'llvm', 'cl', 'squeak', 'js'])],

    '2_gc': [OPT(('--gc',), "Garbage collector", ['boehm', 'ref', 'framework', 'none', 'exact_boehm'])],
    '3_stackless': [OPT(('--stackless',), "Stackless code generation", True)],
    '4_stackless': [OPT(('--old-stackless',), "Stackless code generation (old GenC way)", 'old')],
    '5_merge_if_blocks': [OPT(('--no-if-blocks-merge',), "Do not merge if ... elif ... chains and use a switch statement for them.", False)],
    },


    '4_Compilation options':{
    '_compile': [OPT(('-c', '--compile'), "Compile generated source", GOAL),
                OPT(('--no-compile',), "Don't compile", SKIP_GOAL)],
    },
               
    '5_Run options': {
    '_run': [OPT(('-r', '--run'), "Run compiled code", GOAL),
            OPT(('--no-run',), "Don't run compiled code", SKIP_GOAL)],
    },
    
    '6_General&other options': {
    '0_batch': [OPT(('--batch',), "Don't run interactive helpers", True)],
    '1_lowmem': [OPT(('--lowmem',), "Target should try to save memory", True)],

    '2_huge': [OPT(('--huge',), "Threshold in the number of functions after which only a local call graph and not a full one is displayed", int)],

    '3_text': [OPT(('--text',), "Don't start the pygame viewer", True)], 

    '4_graphserve': [OPT(('--graphserve',), """Serve analysis graphs on port number
(see pypy/translator/tool/pygame/graphclient.py)""", int)],

    '5_fork_before':  [OPT(('--fork-before',), """(UNIX) Create restartable checkpoint before step""", 
                           ['annotate', 'rtype', 'backendopt', 'database', 'source'])],
  
    '6_llinterpret':  [OPT(('--llinterpret',), "Interpret the rtyped flow graphs", GOAL)],
    },

            
}

defaults = {
    'help': False,

    'targetspec': 'targetpypystandalone',
    
    'goals': [],

    'default_goals': ['annotate', 'rtype', 'backendopt', 'source', 'compile'],
    'skipped_goals': ['run'],
    
    'lowmem': False,
    
    'debug': False,
    'insist': False,

    'gc': 'boehm',
    'backend': 'c',
    'stackless': False,
    'merge_if_blocks': True,
    
    'batch': False,
    'text': False,
    'graphserve': None,
    'huge': 100,

    'fork_before': None
}

import py
# we want 2.4 expand_default functionality
optparse = py.compat.optparse
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("translation")
py.log.setconsumer("translation", ansi_log)

class OptHelpFormatter(optparse.IndentedHelpFormatter):

    def expand_default(self, option):
        assert self.parser
        dfls = self.parser.defaults
        defl = ""
        if option.action == 'callback' and option.callback == goal_cb:
            enable, goal = option.callback_args
            if enable == (goal in dfls['default_goals']):
                defl = "[default]"
        else:
            val = dfls.get(option.dest)
            if val is None:
                pass
            elif isinstance(val, bool):
                if bool(val) == (option.action=="store_true"):
                    defl = "[default]"
            else:
                defl = "[default: %s]" % val

        return option.help.replace("%defl", defl)
        
def goal_cb(option, opt, value, parser, enable, goal):
    if enable:
        if goal not in parser.values.ensure_value('goals', []):
            parser.values.goals = parser.values.goals + [goal]
    else:
        if goal not in parser.values.ensure_value('skipped_goals', []):
            parser.values.skipped_goals = parser.values.skipped_goals + [goal]

def load_target(targetspec):
    log.info("Translating target as defined by %s" % targetspec)
    if not targetspec.endswith('.py'):
        targetspec += '.py'
    thismod = sys.modules[__name__]
    targetspec_dic = {
        '__name__': os.path.splitext(os.path.basename(targetspec))[0],
        'translate': thismod}
    sys.path.insert(0, os.path.dirname(targetspec))
    execfile(targetspec, targetspec_dic)
    return targetspec_dic

def parse_options_and_load_target():
    opt_parser = optparse.OptionParser(usage="%prog [options] [target] [target-specific-options]",
                                       prog="translate",
                                       formatter=OptHelpFormatter(),
                                       add_help_option=False)

    opt_parser.disable_interspersed_args()

    for group_name, grp_opts in bunchiter(opts):
        grp = opt_parser.add_option_group(group_name)
        for dest, dest_opts in bunchiter(grp_opts):
            for names, descr, choice in dest_opts:
                opt_setup = {'action': 'store',
                             'dest': dest,
                             'help': descr+" %defl"}
                if choice in (GOAL, SKIP_GOAL):
                    del opt_setup['dest']
                    opt_setup['action'] = 'callback'
                    opt_setup['nargs'] = 0
                    opt_setup['callback'] = goal_cb
                    opt_setup['callback_args'] = (choice is GOAL, dest,)                    
                elif isinstance(choice, list):
                    opt_setup['type'] = 'choice'
                    opt_setup['choices'] = choice
                    opt_setup['metavar'] = "[%s]" % '|'.join(choice)
                elif isinstance(choice, bool):
                    opt_setup['action'] = ['store_false', 'store_true'][choice]
                elif choice is int:
                    opt_setup['type'] = 'int'
                elif choice is str:
                    opt_setup['type'] = 'string'
                else:
                    opt_setup['action'] = 'store_const'
                    opt_setup['const'] = choice

                grp.add_option(*names, **opt_setup)

    # add help back as a flag
    opt_parser.add_option("-h", "--help",
                          action="store_true", dest="help",
                          help="show this help message and exit")

    options, args = opt_parser.parse_args()

    if args:
        arg = args[0]
        args = args[1:]
        if os.path.isfile(arg+'.py'):
            assert not os.path.isfile(arg), (
                "ambiguous file naming, please rename %s" % arg)
            options.targetspec = arg
        elif os.path.isfile(arg) and arg.endswith('.py'):
            options.targetspec = arg[:-3]
        else:
            args = [arg] + args

    # for help, applied later
    opt_parser.set_defaults(**defaults)

    targetspec = options.ensure_value('targetspec', opt_parser.defaults['targetspec'])
    targetspec_dic = load_target(targetspec)

    if args and not targetspec_dic.get('take_options', False):
        log.WARNING("target specific arguments supplied but will be ignored: %s" % ' '.join(args))

    # target specific defaults taking over
    if 'opt_defaults' in targetspec_dic:
        opt_parser.set_defaults(**targetspec_dic['opt_defaults'])

    if options.help:
        opt_parser.print_help()
        if 'print_help' in targetspec_dic:
            print
            targetspec_dic['print_help']()
        sys.exit(0)

    # apply defaults
    for name, val in opt_parser.defaults.iteritems():
        options.ensure_value(name, val)

    # tweak: default_goals into default_goal
    del options.default_goals
    options.default_goal = 'compile'
    
    return targetspec_dic, options, args

def log_options(options, header="options in effect"):
    # list options (xxx filter, filter for target)
    log('%s:' % header)
    optnames = options.__dict__.keys()
    optnames.sort()
    for name in optnames:
        optvalue = getattr(options, name)
        log('%25s: %s' %(name, optvalue))
   
def main():
    targetspec_dic, options, args = parse_options_and_load_target()

    from pypy.translator import translator
    from pypy.translator import driver
    from pypy.translator.tool.pdbplus import PdbPlusShow
 
    t = translator.TranslationContext()

    class ServerSetup:
        async_server = None
        
        def __call__(self, port=None, async_only=False):
            if self.async_server is not None:
                return self.async_server
            elif port is not None:
                from pypy.translator.tool.graphserver import run_async_server
                serv_start, serv_show, serv_stop = self.async_server = run_async_server(t, options, port)
                return serv_start, serv_show, serv_stop
            elif not async_only:
                from pypy.translator.tool.graphserver import run_server_for_inprocess_client
                return run_server_for_inprocess_client(t, options)

    server_setup = ServerSetup()
    server_setup(options.graphserve, async_only=True)

    pdb_plus_show = PdbPlusShow(t) # need a translator to support extended commands

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

        if options.batch:
            log.event("batch mode, not calling interactive helpers")
            return
        
        log.event("start debugger...")

        pdb_plus_show.start(tb, server_setup, graphic=not options.text)

    log_options(options)

    try:
        drv = driver.TranslationDriver.from_targetspec(targetspec_dic, options, args,
                                                      empty_translator=t,
                                                      disable=options.skipped_goals,
                                                      default_goal='compile')
        pdb_plus_show.expose({'drv': drv})

        if drv.exe_name is None and '__name__' in targetspec_dic:
            drv.exe_name = targetspec_dic['__name__'] + '-%(backend)s'

        goals = options.goals
        drv.proceed(goals)
        
    except SystemExit:
        raise
    except:
        debug(True)
        raise SystemExit(1)
    else:
        debug(False)


if __name__ == '__main__':
    main()
