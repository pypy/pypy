import sys, os, re
import subprocess, socket
import traceback, linecache
from contextlib import contextmanager
try:
    import readline
except ImportError:
    pass

from rpython.translator.revdb.process import ReplayProcessGroup
from rpython.translator.revdb.process import Breakpoint

r_cmdline = re.compile(r"([a-zA-Z0-9_]\S*|.)\s*(.*)")
r_dollar_num = re.compile(r"\$(\d+)\b")


class RevDebugControl(object):

    def __init__(self, revdb_log_filename, executable=None,
                 pygments_background=None):
        with open(revdb_log_filename, 'rb') as f:
            header = f.readline()
        assert header.endswith('\n')
        fields = header[:-1].split('\t')
        if len(fields) < 2 or fields[0] != 'RevDB:':
            raise ValueError("file %r is not a RevDB log" % (
                revdb_log_filename,))
        if executable is None:
            executable = fields[1]
        if not os.path.isfile(executable):
            raise ValueError("executable %r not found" % (executable,))
        linecacheoutput = self.getlinecacheoutput(pygments_background)
        self.pgroup = ReplayProcessGroup(executable, revdb_log_filename,
                                         linecacheoutput)
        self.print_extra_pending_info = None

    def interact(self):
        self.last_command = 'help'
        self.previous_time = None
        self.previous_thread = 0
        while True:
            prompt = self.print_lines_before_prompt()
            try:
                while True:
                    cmdline = self.display_prompt(prompt)
                    self.run_command(cmdline)
                    prompt = self.print_lines_before_prompt()
            except KeyboardInterrupt:
                rtime = self.previous_time or 1
                print
                print 'KeyboardInterrupt: restoring state at time %d...' % (
                    rtime,)
                self.pgroup.recreate_subprocess(rtime)
                self.last_command = ''
                self.previous_thread = '?'
                self.previous_time = '?'

    def print_lines_before_prompt(self):
        last_time = self.pgroup.get_current_time()
        if last_time != self.previous_time:
            print
            if self.pgroup.get_current_thread() != self.previous_thread:
                self.previous_thread = self.pgroup.get_current_thread()
                if self.previous_thread == 0:
                    print ('-------------------- in main thread #0 '
                           '--------------------')
                else:
                    print ('-------------------- in non-main thread '
                           '#%d --------------------' % (self.previous_thread,))
            self.pgroup.update_watch_values()
            last_time = self.pgroup.get_current_time()
        if self.print_extra_pending_info:
            print self.print_extra_pending_info
            self.print_extra_pending_info = None
        if last_time != self.previous_time:
            self.pgroup.show_backtrace(complete=0)
            self.previous_time = last_time
        prompt = '(%d)$ ' % last_time
        return prompt

    def display_prompt(self, prompt):
        try:
            cmdline = raw_input(prompt).strip()
        except EOFError:
            print
            cmdline = 'quit'
        if not cmdline:
            cmdline = self.last_command
        return cmdline

    def run_command(self, cmdline):
        match = r_cmdline.match(cmdline)
        if not match:
            return
        self.last_command = cmdline
        command, argument = match.groups()
        try:
            runner = getattr(self, 'command_' + command)
        except AttributeError:
            print >> sys.stderr, "no command '%s', try 'help'" % (command,)
        else:
            try:
                runner(argument)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                traceback.print_exc()
                print >> sys.stderr
                print >> sys.stderr, 'Something went wrong.  You are now',
                print >> sys.stderr, 'in a pdb; press Ctrl-D to continue.'
                import pdb; pdb.post_mortem(sys.exc_info()[2])
                print >> sys.stderr
                print >> sys.stderr, 'You are back running %s.' % (
                    sys.argv[0],)

    def command_help(self, argument):
        """Display commands summary"""
        print 'Available commands:'
        lst = dir(self)
        commands = [(name[len('command_'):], getattr(self, name))
                    for name in lst
                        if name.startswith('command_')]
        seen = {}
        for name, func in commands:
            seen.setdefault(func, []).append(name)
        for _, func in commands:
            if func in seen:
                names = seen.pop(func)
                names.sort(key=len, reverse=True)
                docstring = func.__doc__ or 'undocumented'
                print '\t%-16s %s' % (', '.join(names), docstring)

    def command_quit(self, argument):
        """Exit the debugger"""
        self.pgroup.close()
        sys.exit(0)
    command_q = command_quit

    def command_go(self, argument):
        """Jump to time ARG"""
        arg = int(argument or self.pgroup.get_current_time())
        self.pgroup.jump_in_time(arg)

    def command_info(self, argument):
        """Display various info ('info help' for more)"""
        display = getattr(self, 'cmd_info_' + argument, self.cmd_info_help)
        return display()

    def cmd_info_help(self):
        """Display info topics summary"""
        print 'Available info topics:'
        for name in dir(self):
            if name.startswith('cmd_info_'):
                command = name[len('cmd_info_'):]
                docstring = getattr(self, name).__doc__ or 'undocumented'
                print '\tinfo %-12s %s' % (command, docstring)

    def cmd_info_paused(self):
        """List current paused subprocesses"""
        lst = [str(n) for n in sorted(self.pgroup.paused)]
        print ', '.join(lst)

    def _bp_kind(self, num):
        break_at = self.pgroup.all_breakpoints.num2break.get(num, '??')
        if break_at[0] == 'B':
            kind = 'breakpoint'
            name = break_at[4:]
        elif break_at[0] == 'W':
            kind = 'watchpoint'
            name = self.pgroup.all_breakpoints.sources.get(num, '??')
        elif num == -3:
            kind = 'stoppoint'
            name = 'explicit stop'
        elif num == -4:
            kind = 'switchpoint'
            name = 'thread switch'
        else:
            kind = '?????point'
            name = repr(break_at)
        return kind, name

    def _bp_new(self, source_expr, break_code, break_at, nids=None):
        b = self.pgroup.edit_breakpoints()
        new = 1
        while new in b.num2break:
            new += 1
        b.set_num2break(new, break_code, break_at)
        b.sources[new] = source_expr
        if break_code == 'W':
            b.watchvalues[new] = ''
            if nids:
                b.watchuids[new] = self.pgroup.nids_to_uids(nids)
        return new

    def cmd_info_breakpoints(self):
        """List current breakpoints and watchpoints"""
        lst = self.pgroup.all_breakpoints.num2break.keys()
        if lst:
            for num in sorted(lst):
                kind, name = self._bp_kind(num)
                print '\t%s %d: %s' % (kind, num, name)
        else:
            print 'no breakpoints/watchpoints.'
    cmd_info_watchpoints = cmd_info_breakpoints

    def move_forward(self, steps):
        self.remove_tainting()
        try:
            self.pgroup.go_forward(steps)
            return None
        except Breakpoint as b:
            self.hit_breakpoints(b)
            return b

    def move_backward(self, steps):
        try:
            self.pgroup.go_backward(steps)
            return None
        except Breakpoint as b:
            self.hit_breakpoints(b, backward=True)
            return b

    def hit_breakpoints(self, b, backward=False):
        printing = []
        for num in b.regular_breakpoint_nums():
            kind, name = self._bp_kind(num)
            printing.append('%s %s%s: %s' % (
                'Reverse-hit' if backward else 'Hit',
                kind,
                '' if kind == 'stoppoint' else ' %d' % (num,),
                name))
        self.print_extra_pending_info = '\n'.join(printing)
        if self.pgroup.get_current_time() != b.time:
            target_time = b.time
            if backward and any(self._bp_kind(num)[0] == 'watchpoint'
                                for num in b.regular_breakpoint_nums()):
                target_time += 1
            self.pgroup.jump_in_time(target_time)

    def remove_tainting(self):
        if self.pgroup.is_tainted():
            self.pgroup.jump_in_time(self.pgroup.get_current_time())
            assert not self.pgroup.is_tainted()

    def command_step(self, argument):
        """Run forward ARG steps (default 1)"""
        arg = int(argument or '1')
        self.move_forward(arg)
    command_s = command_step

    def command_bstep(self, argument):
        """Run backward ARG steps (default 1)"""
        arg = int(argument or '1')
        self.move_backward(arg)
    command_bs = command_bstep

    @contextmanager
    def _stack_id_break(self, stack_id):
        # add temporarily a breakpoint that hits when we enter/leave
        # a frame from/to the frame identified by 'stack_id'
        b = self.pgroup.edit_breakpoints()
        b.stack_id = stack_id
        try:
            yield
        finally:
            b.stack_id = 0

    @contextmanager
    def _thread_num_break(self, thread_num):
        # add temporarily a breakpoint that hits when we enter/leave
        # the given thread
        b = self.pgroup.edit_breakpoints()
        b.thread_num = thread_num
        try:
            yield
        finally:
            b.thread_num = -1

    def command_next(self, argument):
        """Run forward for one step, skipping calls"""
        while True:
            stack_id = self.pgroup.get_stack_id(is_parent=False)
            with self._stack_id_break(stack_id):
                b = self.move_forward(1)
            while b is not None:
                # if we hit a regular breakpoint, stop
                if any(b.regular_breakpoint_nums()):
                    return
                # we hit only calls and returns inside stack_id.  If the
                # last one of these is a "return", then we're now back inside
                # stack_id, so stop
                if b.nums[-1] == -2:
                    break
                # else, the last one is a "call", so we entered another frame.
                # Continue running until the next call/return event occurs
                # inside stack_id
                with self._stack_id_break(stack_id):
                    b = self.move_forward(self.pgroup.get_max_time() -
                                          self.pgroup.get_current_time())
                # and then look at that 'b' again (closes the loop)

            # we might be at a "<<" position on the same line as before,
            # which returns a get_hiddenpos_level() value of 1.  Continue
            # until we reach a get_hiddenpos_level() value of 0.
            if b is None or self.pgroup.get_hiddenpos_level() == 0:
                break
    command_n = command_next

    def command_bnext(self, argument):
        """Run backward for one step, skipping calls"""
        while True:
            stack_id = self.pgroup.get_stack_id(is_parent=False)
            with self._stack_id_break(stack_id):
                b = self.move_backward(1)
            while b is not None:
                # if we hit a regular breakpoint, stop
                if any(b.regular_breakpoint_nums()):
                    return
                # we hit only calls and returns inside stack_id.  If the
                # first one of these is a "call", then we're now back inside
                # stack_id, so stop
                if b.nums[0] == -1:
                    break
                # else, the first one is a "return", so before, we were
                # inside a different frame.  Continue running until the next
                # call/return event occurs inside stack_id
                with self._stack_id_break(stack_id):
                    b = self.move_backward(self.pgroup.get_current_time() - 1)
                # and then look at that 'b' again (closes the loop)

            # we might be at a "<<" position on the same line as before,
            # which returns a get_hiddenpos_level() value of 1.  Continue
            # until we reach a get_hiddenpos_level() value of 0.
            if self.pgroup.get_hiddenpos_level() == 0:
                break
    command_bn = command_bnext

    def command_finish(self, argument):
        """Run forward until the current function finishes"""
        stack_id = self.pgroup.get_stack_id(is_parent=True)
        if stack_id == 0:
            print 'No caller.'
        else:
            with self._stack_id_break(stack_id):
                self.command_continue('')

    def command_bfinish(self, argument):
        """Run backward until the current function is called"""
        stack_id = self.pgroup.get_stack_id(is_parent=True)
        if stack_id == 0:
            print 'No caller.'
        else:
            with self._stack_id_break(stack_id):
                self.command_bcontinue('')

    def command_continue(self, argument):
        """Run forward"""
        self.move_forward(self.pgroup.get_max_time() -
                          self.pgroup.get_current_time())
    command_c = command_continue

    def command_bcontinue(self, argument):
        """Run backward"""
        self.move_backward(self.pgroup.get_current_time() - 1)
    command_bc = command_bcontinue

    def _cmd_thread(self, argument, cmd_continue):
        argument = argument.lstrip('#')
        if argument:
            arg = int(argument)
            if arg == self.pgroup.get_current_thread():
                print 'Thread #%d is already the current one.' % (arg,)
                return
        else:
            # use the current thread number to detect switches to any
            # other thread (this works because revdb.c issues a
            # breakpoint whenever there is a switch FROM or TO the
            # thread '#arg').
            arg = self.pgroup.get_current_thread()
        #
        with self._thread_num_break(arg):
            cmd_continue('')

    def command_nthread(self, argument):
        """Run forward until thread switch (optionally to #ARG)"""
        self._cmd_thread(argument, self.command_continue)

    def command_bthread(self, argument):
        """Run backward until thread switch (optionally to #ARG)"""
        self._cmd_thread(argument, self.command_bcontinue)

    def command_print(self, argument):
        """Print an expression or execute a line of code"""
        # locate which $NUM appear used in the expression
        nids = map(int, r_dollar_num.findall(argument))
        self.pgroup.print_cmd(argument, nids=nids)
    command_p = command_print
    locals()['command_!'] = command_print

    def command_backtrace(self, argument):
        """Show the backtrace"""
        self.pgroup.show_backtrace(complete=1)
    command_bt = command_backtrace

    def command_list(self, argument):
        """Show the current function"""
        self.pgroup.show_backtrace(complete=2)

    def command_locals(self, argument):
        """Show the locals"""
        self.pgroup.show_locals()

    def command_break(self, argument):
        """Add a breakpoint"""
        if not argument:
            print "Break where?"
            return
        num = self._bp_new(argument, 'B', argument)
        b = self.pgroup.edit_breakpoints()
        old = b.num2break[num]
        self.pgroup.update_breakpoints()
        new = b.num2break.get(num)
        if old == new:
            print "Breakpoint %d added" % (num,)
        elif new is None:
            print "Breakpoint not added"
        else:
            kind, name = self._bp_kind(num)
            print "Breakpoint %d added as: %s" % (num, name)
    command_b = command_break

    def command_delete(self, argument):
        """Delete a breakpoint/watchpoint"""
        arg = int(argument)
        b = self.pgroup.edit_breakpoints()
        if arg not in b.num2break:
            print "No breakpoint/watchpoint number %d" % (arg,)
        else:
            kind, name = self._bp_kind(arg)
            b.num2break.pop(arg, '')
            b.sources.pop(arg, '')
            b.watchvalues.pop(arg, '')
            b.watchuids.pop(arg, '')
            print "%s %d deleted: %s" % (kind.capitalize(), arg, name)

    def command_watch(self, argument):
        """Add a watchpoint (use $NUM in the expression to watch)"""
        if not argument:
            print "Watch what?"
            return
        #
        ok_flag, compiled_code = self.pgroup.compile_watchpoint_expr(argument)
        if not ok_flag:
            print compiled_code     # the error message
            print 'Watchpoint not added'
            return
        #
        nids = map(int, r_dollar_num.findall(argument))
        ok_flag, text = self.pgroup.check_watchpoint_expr(compiled_code, nids)
        if not ok_flag:
            print text
            print 'Watchpoint not added'
            return
        #
        new = self._bp_new(argument, 'W', compiled_code, nids=nids)
        self.pgroup.update_watch_values()
        print "Watchpoint %d added" % (new,)

    def getlinecacheoutput(self, pygments_background):
        if not pygments_background or pygments_background == 'off':
            return
        try:
            from pygments import highlight
            from pygments.lexers import PythonLexer
            from pygments.formatters import TerminalFormatter
        except ImportError as e:
            print >> sys.stderr, 'ImportError: %s' % (e,)
            return None
        #
        lexer = PythonLexer()
        fmt = TerminalFormatter(bg=pygments_background)
        #
        def linecacheoutput(filename, lineno):
            line = linecache.getline(filename, lineno)
            return highlight(line, lexer, fmt)
        return linecacheoutput
