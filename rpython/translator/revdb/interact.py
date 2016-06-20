import sys, re
import subprocess, socket
import traceback
from rpython.translator.revdb.process import ReplayProcessGroup, maxint64

r_cmdline = re.compile(r"(\S+)\s*(.*)")


class RevDebugControl(object):

    def __init__(self, revdb_log_filename, executable=None):
        with open(revdb_log_filename, 'rb') as f:
            header = f.readline()
        fields = header.split('\t')
        if len(fields) < 2 or fields[0] != 'RevDB:':
            raise ValueError("file %r is not a RevDB log" % (
                revdb_log_filename,))
        if executable is None:
            executable = fields[1]
        self.pgroup = ReplayProcessGroup(executable, revdb_log_filename)

    def interact(self):
        last_command = 'help'
        while True:
            last_time = self.pgroup.get_current_time()
            prompt = '(%d)$ ' % last_time
            sys.stdout.write(prompt)
            sys.stdout.flush()
            try:
                cmdline = raw_input().strip()
            except EOFError:
                print
                cmdline = 'quit'
            if not cmdline:
                cmdline = last_command
            match = r_cmdline.match(cmdline)
            if not match:
                continue
            last_command = cmdline
            command, argument = match.groups()
            try:
                runner = getattr(self, 'command_' + command)
            except AttributeError:
                print >> sys.stderr, "no command '%s', try 'help'" % (command,)
            else:
                try:
                    runner(argument)
                except Exception as e:
                    traceback.print_exc()

    def command_help(self, argument):
        """Display commands summary"""
        print 'Available commands:'
        for name in dir(self):
            if name.startswith('command_'):
                command = name[len('command_'):]
                docstring = getattr(self, name).__doc__ or 'undocumented'
                print '\t%-12s %s' % (command, docstring)

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

    def command_step(self, argument):
        """Run forward ARG steps (default 1)"""
        arg = int(argument or '1')
        if self.pgroup.is_tainted():
            self.pgroup.jump_in_time(self.pgroup.get_current_time() + arg)
        else:
            self.pgroup.go_forward(arg)
    command_s = command_step

    def command_bstep(self, argument):
        """Run backward ARG steps (default 1)"""
        arg = int(argument or '1')
        self.pgroup.jump_in_time(self.pgroup.get_current_time() - arg)
    command_bs = command_bstep

    def command_continue(self, argument):
        """Run forward"""
        self.pgroup.jump_in_time(maxint64)
    command_c = command_continue

    def command_print(self, argument):
        """Print an expression"""
        self.pgroup.print_cmd(argument)
    command_p = command_print

    def command_backtrace(self, argument):
        """Show the backtrace"""
        self.pgroup.show_backtrace()
    command_bt = command_backtrace

    def command_locals(self, argument):
        """Show the locals"""
        self.pgroup.show_locals()
