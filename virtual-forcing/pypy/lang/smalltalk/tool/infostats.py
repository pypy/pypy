import pstats
p = pstats.Stats('compile_method.txt')
#print p.print_callers('as_context_get_shadow')
#print p.print_callers('s_active_context')
p.sort_stats('time', 'cum').print_stats(.5)
