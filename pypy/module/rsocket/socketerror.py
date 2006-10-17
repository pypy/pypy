import sys, errno

if sys.platform == 'win32':
    WIN32_ERROR_MESSAGES = {
        errno.WSAEINTR:  "Interrupted system call",
        errno.WSAEBADF:  "Bad file descriptor",
        errno.WSAEACCES: "Permission denied",
        errno.WSAEFAULT: "Bad address",
        errno.WSAEINVAL: "Invalid argument",
        errno.WSAEMFILE: "Too many open files",
        errno.WSAEWOULDBLOCK:
          "The socket operation could not complete without blocking",
        errno.WSAEINPROGRESS: "Operation now in progress",
        errno.WSAEALREADY: "Operation already in progress",
        errno.WSAENOTSOCK: "Socket operation on non-socket",
        errno.WSAEDESTADDRREQ: "Destination address required",
        errno.WSAEMSGSIZE: "Message too long",
        errno.WSAEPROTOTYPE: "Protocol wrong type for socket",
        errno.WSAENOPROTOOPT: "Protocol not available",
        errno.WSAEPROTONOSUPPORT: "Protocol not supported",
        errno.WSAESOCKTNOSUPPORT: "Socket type not supported",
        errno.WSAEOPNOTSUPP: "Operation not supported",
        errno.WSAEPFNOSUPPORT: "Protocol family not supported",
        errno.WSAEAFNOSUPPORT: "Address family not supported",
        errno.WSAEADDRINUSE: "Address already in use",
        errno.WSAEADDRNOTAVAIL: "Can't assign requested address",
        errno.WSAENETDOWN: "Network is down",
        errno.WSAENETUNREACH: "Network is unreachable",
        errno.WSAENETRESET: "Network dropped connection on reset",
        errno.WSAECONNABORTED: "Software caused connection abort",
        errno.WSAECONNRESET: "Connection reset by peer",
        errno.WSAENOBUFS: "No buffer space available",
        errno.WSAEISCONN: "Socket is already connected",
        errno.WSAENOTCONN: "Socket is not connected",
        errno.WSAESHUTDOWN: "Can't send after socket shutdown",
        errno.WSAETOOMANYREFS: "Too many references: can't splice",
        errno.WSAETIMEDOUT: "Operation timed out",
        errno.WSAECONNREFUSED: "Connection refused",
        errno.WSAELOOP: "Too many levels of symbolic links",
        errno.WSAENAMETOOLONG: "File name too long",
        errno.WSAEHOSTDOWN: "Host is down",
        errno.WSAEHOSTUNREACH: "No route to host",
        errno.WSAENOTEMPTY: "Directory not empty",
        errno.WSAEPROCLIM: "Too many processes",
        errno.WSAEUSERS: "Too many users",
        errno.WSAEDQUOT: "Disc quota exceeded",
        errno.WSAESTALE: "Stale NFS file handle",
        errno.WSAEREMOTE: "Too many levels of remote in path",
        errno.WSASYSNOTREADY: "Network subsystem is unvailable",
        errno.WSAVERNOTSUPPORTED: "WinSock version is not supported",
        errno.WSANOTINITIALISED: "Successful WSAStartup() not yet performed",
        errno.WSAEDISCON: "Graceful shutdown in progress",

        # Resolver errors
        # XXX Not exported by errno. Replace by the values in winsock.h
        # errno.WSAHOST_NOT_FOUND: "No such host is known",
        # errno.WSATRY_AGAIN: "Host not found, or server failed",
        # errno.WSANO_RECOVERY: "Unexpected server error encountered",
        # errno.WSANO_DATA: "Valid name without requested data",
        # errno.WSANO_ADDRESS: "No address, look for MX record",
        }

    def socket_strerror(errno):
        return WIN32_ERROR_MESSAGES.get(errno, "winsock error")
else:
    from pypy.module.rsocket import ctypes_socket as _c
    def socket_strerror(errno):
        return _c.strerror(errno)
