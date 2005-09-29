#! /usr/bin/env python
"""
Command-line options for translate_pypy:

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
    '_backopt':  [OPT(('-o', '--backopt'), "Do backend optimisations", GOAL),
                 OPT(('--no-backopt',), "Don't do backend optimisations", SKIP_GOAL)],
    },

    '3_Code generation options': {
    '0_source': [OPT(('-s', '--source'), "Generate source code", GOAL),
               OPT(('--no-source',), "Don't generate source code", SKIP_GOAL)],

    '1_backend': [OPT(('-b', '--backend'), "Backend", ['c', 'llvm'])],

    '2_gc': [OPT(('--gc',), "Garbage collector", ['ref', 'boehm', 'none'])],
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

    },

                    
    #'Process options':[
    #    ['-f', '--fork', 
    #           "(UNIX) Create restartable checkpoint after annotation [,specialization]",
    #                        [['fork1','fork2']], [] ],
            
}

defaults = {
    'targetspec': 'targetpypystandalone',
    
    'goals': [],

    'default_goals': ['annotate', 'rtype', 'backopt', 'source', 'compile'],
    'skipped_goals': ['run'],
    
    'lowmem': False,
    
    'debug': False,
    'insist': False,

    'gc': 'boehm',
    'backend': 'c',
    
    'batch': False,
    'text': False,
    'graphserve': None,
    'huge': 100,
}

import py
# we want 2.4 expand_default functionality
optparse = py.compat.optparse


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
        parser.values.goals = parser.values.goals + [goal]
    else:
        parser.values.skipped_goals = parser.values.skipped_goals + [goal]

def load_target(targetspec):
    if not targetspec.endswith('.py'):
        targetspec += '.py'
    targetspec_dic = {}
    sys.path.insert(0, os.path.dirname(targetspec))
    #xxx print 
    execfile(targetspec, targetspec_dic)
    return targetspec_dic

def parse_options_and_load_target():
    opt_parser = optparse.OptionParser(usage="%prog [options] [target]", prog="translate_pypy",
                                       formatter=OptHelpFormatter())
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
                elif isinstance(choice, bool):
                    opt_setup['action'] = ['store_false', 'store_true'][choice]
                elif choice is int:
                    opt_setup['type'] = 'int'
                elif choice is str:
                    opt_setup['type'] = 'string'

                grp.add_option(*names, **opt_setup)

    opt_parser.set_defaults(**defaults)

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

    targespec_dic = load_target(options.targetspec)
    
    return targespec_dic, options, args

def main():
    targetspec_dic, options, args = parse_options_and_load_target()

    from pypy.translator import translator
    from pypy.translator.goal import driver
    from pypy.translator.tool.pdbplus import PdbPlusShow
    from pypy.translator.tool.graphserver import run_async_server

    t = translator.Translator()

    if options.graphserve:
        serv_start, serv_show, serv_stop, serv_cleanup = run_async_server(t, options.graphserve)
        def server_setup():
            return serv_start, serv_show, serv_stop, serv_cleanup
    else:
        def server_setup():
            from pypy.translator.tool.pygame.server import run_translator_server
            return run_translator_server(t, options)

    pdb_plus_show = PdbPlusShow(t) # need a translator to support extended commands

    def debug(got_error):
        tb = None
        if got_error:
            import traceback
            exc, val, tb = sys.exc_info()
            print >> sys.stderr
            traceback.print_exception(exc, val, tb)
            print >> sys.stderr
            
            block = getattr(val, '__annotator_block', None)
            if block:
                print '-'*60
                t.about(block)
                print '-'*60
            print
        else:
            print '-'*60
            print 'Done.'
            print

        if options.batch:
            print >>sys.stderr, "batch mode, not calling interactive helpers"
            return

        pdb_plus_show.start(tb, server_setup, graphic=not options.text)

    try:
        drv = driver.TranslationDriver.from_targetspec(targetspec_dic, options, args,
                                                      empty_translator=t,
                                                      disable=options.skipped_goals,
                                                      default_goal='compile')
        pdb_plus_show.expose({'drv': drv})

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
