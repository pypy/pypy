"""
module to access local filesystem pathes 
(mostly filename manipulations but also file operations)
"""
import os, sys, stat

import py
#__________________________________________________________
#
# Local Path Posix Mixin 
#__________________________________________________________

class PosixMixin:
    # an instance needs to be a local path instance 
    def owner(self):
        """ return owner name of file. """
        try:
            from pwd import getpwuid
            return getpwuid(self.stat().st_uid)[0]
        except:
            self._except(sys.exc_info())

    def group(self):
        """ return group name of file. """
        try:
            from grp import getgrgid
            return getgrgid(self.stat().st_gid)[0]
        except:
            self._except(sys.exc_info())

    def mode(self):
        """ return permission mode of the path object """
        return self.stat().st_mode

    def chmod(self, mode, rec=0):
        """ change permissions to the given mode. If mode is an
            integer it directly encodes the os-specific modes. 
            (xxx if mode is a string then it specifies access rights
            in '/bin/chmod' style, e.g. a+r). 
            if rec is True perform recursively. 
        """
        try:
            if not isinstance(mode, int):
                raise NotImplementedError
            if rec:
                for x in self.visit():
                    os.chmod(str(x), mode) 
            os.chmod(str(self), mode) 
        except:
            self._except(sys.exc_info())

    def chown(self, user, group, rec=0):
        """ change ownership to the given user and group. 
            user and group may be specified by a number or
            by a name.  if rec is True change ownership 
            recursively. 
        """
        uid = getuserid(user)
        gid = getgroupid(group)
        try:
            if rec:
                for x in self.visit(rec=py.path.checker(link=0)):
                    os.chown(str(x), uid, gid) 
            os.chown(str(self), uid, gid) 
        except:
            self._except(sys.exc_info())

    def readlink(self):
        """ return value of a symbolic link. """ 
        try:
            return os.readlink(self.strpath)
        except:
            self._except(sys.exc_info())

    def mklinkto(self, oldname): 
        """ hard link to an old name. """ 
        try:
            os.link(str(oldname), str(self)) 
        except:
            self._except(sys.exc_info())

    def mksymlinkto(self, value, absolute=1):
        """ create a symbolic link with the given value (pointing to another name). """ 
        try:
            if absolute:
                os.symlink(str(value), self.strpath)
            else:
                base = self.common(value)
                # with posix local paths '/' is always a common base 
                relsource = self.__class__(value).relto(base)
                reldest = self.relto(base)
                n = reldest.count(self.sep)
                target = self.sep.join(('..', )*n + (relsource, ))
                os.symlink(target, self.strpath)
        except:
            self._except(sys.exc_info())


def getuserid(user):
    import pwd
    if isinstance(user, int):
        return user
    entry = pwd.getpwnam(user)
    return entry[2]

def getgroupid(group):
    import grp
    if isinstance(group, int):
        return group
    entry = grp.getgrnam(group)
    return entry[2]
