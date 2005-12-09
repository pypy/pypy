#ifdef LL_NEED__SOCKET /* isolate */

#ifdef MS_WINDOWS
  /* winsock2.h has already been included before windows.h in thread_nt.h */
#else
# include <arpa/inet.h>
# include <sys/types.h>
# include <sys/socket.h>
# include <netdb.h>
# include <netinet/in.h>
#endif

static int
setipaddr(char *name, struct sockaddr *addr_ret, size_t addr_ret_size, int af);
int LL__socket_ntohs(int htons);
int LL__socket_htons(int ntohs);
long LL__socket_ntohl(long htonl);
long LL__socket_htonl(long ntohl);
int LL__socket_newsocket(int family, int type, int protocol);
RPyString *LL__socket_gethostname(void);
RPyString *LL__socket_gethostbyname(RPyString *name);
struct RPyOpaque_ADDRINFO *LL__socket_getaddrinfo(RPyString *host, RPyString *port, 
						  int family, int socktype, 
						  int proto, int flags);
RPySOCKET_ADDRINFO *LL__socket_nextaddrinfo(struct RPyOpaque_ADDRINFO *addr);

#ifndef PYPY_NOT_MAIN_FILE

#ifdef MS_WINDOWS
# pragma comment(lib, "ws2_32.lib")
# include <Ws2tcpip.h>
# if _MSC_VER >= 1300
#  define HAVE_ADDRINFO
#  define HAVE_SOCKADDR_STORAGE
#  define HAVE_GETADDRINFO
#  define HAVE_GETNAMEINFO
#  define ENABLE_IPV6
# endif
#endif

#include "addrinfo.h"

#ifndef HAVE_INET_PTON
int inet_pton(int af, const char *src, void *dst);
const char *inet_ntop(int af, const void *src, char *dst, socklen_t size);
#endif

/* I know this is a bad practice, but it is the easiest... */
#if !defined(HAVE_GETADDRINFO)
/* avoid clashes with the C library definition of the symbol. */
#define getaddrinfo fake_getaddrinfo
#define gai_strerror fake_gai_strerror
#define freeaddrinfo fake_freeaddrinfo
#include "getaddrinfo.c"
#endif
#if !defined(HAVE_GETNAMEINFO)
#define getnameinfo fake_getnameinfo
#include "getnameinfo.c"
#endif


int LL__socket_ntohs(int htons)
{
    return (int)ntohs((short) htons);
}

int LL__socket_htons(int ntohs)
{
    return (int)htons((short) ntohs);
}

long LL__socket_ntohl(long htonl)
{
    return ntohl(htonl);
}

long LL__socket_htonl(long ntohl)
{
    return htonl(ntohl);
}

// XXX Check what should be done threading-wise around blocking system calls

int LL__socket_newsocket(int family, int type, int protocol)
{
    int fd;

    fd = socket(family, type, protocol);

#ifdef MS_WINDOWS
    if (fd == INVALID_SOCKET)
#else
    if (fd < 0)
#endif
    {
        // Raise OSError instead of socket.error for convenience.
        // XXX For some reason the errno attribute of the OSError is not set
        // at interpreter level. Investigate ...
        RPYTHON_RAISE_OSERROR(errno);
    }
}

void LL__socket_connect(int fd, RPyString *host, int port)
{
    struct sockaddr_in addr;
    
    if (setipaddr(RPyString_AsString(host), (struct sockaddr *) &addr,
		      sizeof(addr), AF_INET) < 0) {
        // XXX raise some error here
    }
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    if (connect(fd, &addr, sizeof(addr)) < 0) {
        // XXX raise some error here
    }
}

RPySOCKET_SOCKNAME *LL__socket_getpeername(int fd)
{
    struct sockaddr_in addr; // XXX IPv4 only
    int addr_len;
    RPySOCKET_SOCKNAME* sockname;
    RPyString* host;
    
    memset((void *) &addr, '\0', sizeof(addr));
    addr_len = sizeof(addr);
    if (getpeername(fd, (struct sockaddr *) &addr, &addr_len) < 0) {
        // XXX raise some error here
    }
    
    host = RPyString_FromString(inet_ntoa(addr.sin_addr));
#if !defined(USING_BOEHM_GC) && !defined(USING_NO_GC)
    host->refcount--; // XXX this is not sane, but there is no better way
                      // at the moment.
#endif
    return ll__socket_sockname(host, addr.sin_port, 0, 0);
}

/* ____________________________________________________________________________ */

/* Lock to allow python interpreter to continue, but only allow one
   thread to be in gethostbyname or getaddrinfo */
#if defined(USE_GETHOSTBYNAME_LOCK) || defined(USE_GETADDRINFO_LOCK)
/* XXX */
/* RPyThread_type_lock netdb_lock; */
#endif

#ifdef USE_GETADDRINFO_LOCK
/* XXX not used */
/* #define ACQUIRE_GETADDRINFO_LOCK PyThread_acquire_lock(netdb_lock, 1); */
/* #define RELEASE_GETADDRINFO_LOCK PyThread_release_lock(netdb_lock); */ 
#else
/* #define ACQUIRE_GETADDRINFO_LOCK */
/* #define RELEASE_GETADDRINFO_LOCK */
#endif


/* Convert a string specifying a host name or one of a few symbolic
   names to a numeric IP address.  This usually calls gethostbyname()
   to do the work; the names "" and "<broadcast>" are special.
   Return the length (IPv4 should be 4 bytes), or negative if
   an error occurred; then an exception is raised. */

static int
setipaddr(char *name, struct sockaddr *addr_ret, size_t addr_ret_size, int af)
{
	struct addrinfo hints, *res;
	int error;
	int d1, d2, d3, d4;
	char ch;

	memset((void *) addr_ret, '\0', sizeof(*addr_ret));
	if (name[0] == '\0') {
		int siz;
		memset(&hints, 0, sizeof(hints));
		hints.ai_family = af;
		hints.ai_socktype = SOCK_DGRAM;	/*dummy*/
		hints.ai_flags = AI_PASSIVE;
		/* XXX Py_BEGIN_ALLOW_THREADS */
		/* XXX ACQUIRE_GETADDRINFO_LOCK */
		error = getaddrinfo(NULL, "0", &hints, &res);
		/* XXX Py_END_ALLOW_THREADS */
		/* We assume that those thread-unsafe getaddrinfo() versions
		   *are* safe regarding their return value, ie. that a
		   subsequent call to getaddrinfo() does not destroy the
		   outcome of the first call. */
		/* XXX RELEASE_GETADDRINFO_LOCK */
		if (error) {
			RPYTHON_RAISE_OSERROR(errno); /* XXX set_gaierror(error);*/
			return -1;
		}
		switch (res->ai_family) {
		case AF_INET:
			siz = 4;
			break;
#ifdef ENABLE_IPV6
		case AF_INET6:
			siz = 16;
			break;
#endif
		default:
			freeaddrinfo(res);
			RPyRaiseSimpleException(PyExc_socket_error,
				"unsupported address family");
			return -1;
		}
		if (res->ai_next) {
			freeaddrinfo(res);
			RPyRaiseSimpleException(PyExc_socket_error,
				"wildcard resolved to multiple address");
			return -1;
		}
		if (res->ai_addrlen < addr_ret_size)
			addr_ret_size = res->ai_addrlen;
		memcpy(addr_ret, res->ai_addr, addr_ret_size);
		freeaddrinfo(res);
		return siz;
	}
	if (name[0] == '<' && strcmp(name, "<broadcast>") == 0) {
		struct sockaddr_in *sin;
		if (af != AF_INET && af != AF_UNSPEC) {
			RPyRaiseSimpleException(PyExc_socket_error,
				"address family mismatched");
			return -1;
		}
		sin = (struct sockaddr_in *)addr_ret;
		memset((void *) sin, '\0', sizeof(*sin));
		sin->sin_family = AF_INET;
#ifdef HAVE_SOCKADDR_SA_LEN
		sin->sin_len = sizeof(*sin);
#endif
		sin->sin_addr.s_addr = INADDR_BROADCAST;
		return sizeof(sin->sin_addr);
	}
	if (sscanf(name, "%d.%d.%d.%d%c", &d1, &d2, &d3, &d4, &ch) == 4 &&
	    0 <= d1 && d1 <= 255 && 0 <= d2 && d2 <= 255 &&
	    0 <= d3 && d3 <= 255 && 0 <= d4 && d4 <= 255) {
		struct sockaddr_in *sin;
		sin = (struct sockaddr_in *)addr_ret;
		sin->sin_addr.s_addr = htonl(
			((long) d1 << 24) | ((long) d2 << 16) |
			((long) d3 << 8) | ((long) d4 << 0));
		sin->sin_family = AF_INET;
#ifdef HAVE_SOCKADDR_SA_LEN
		sin->sin_len = sizeof(*sin);
#endif
		return 4;
	}
	memset(&hints, 0, sizeof(hints));
	hints.ai_family = af;
	/* XXX Py_BEGIN_ALLOW_THREADS */
	/* XXX ACQUIRE_GETADDRINFO_LOCK */
	error = getaddrinfo(name, NULL, &hints, &res);
#if defined(__digital__) && defined(__unix__)
	if (error == EAI_NONAME && af == AF_UNSPEC) {
		/* On Tru64 V5.1, numeric-to-addr conversion fails
		   if no address family is given. Assume IPv4 for now.*/
		hints.ai_family = AF_INET;
		error = getaddrinfo(name, NULL, &hints, &res);
	}
#endif
	/* XXX Py_END_ALLOW_THREADS */
	/* XXX RELEASE_GETADDRINFO_LOCK */ /* see comment in setipaddr() */
	if (error) {
		RPYTHON_RAISE_OSERROR(errno); /* XXX set_gaierror(error); */
		return -1;
	}
	if (res->ai_addrlen < addr_ret_size)
		addr_ret_size = res->ai_addrlen;
	memcpy((char *) addr_ret, res->ai_addr, addr_ret_size);
	freeaddrinfo(res);
	switch (addr_ret->sa_family) {
	case AF_INET:
		return 4;
#ifdef ENABLE_IPV6
	case AF_INET6:
		return 16;
#endif
	default:
		RPyRaiseSimpleException(PyExc_socket_error,
					"unknown address family");
		return -1;
	}
}


/* Create a string object representing an IP address.
   This is always a string of the form 'dd.dd.dd.dd' (with variable
   size numbers). */

RPyString *makeipaddr(struct sockaddr *addr, int addrlen)
{
	char buf[NI_MAXHOST];
	int error;

	error = getnameinfo(addr, addrlen, buf, sizeof(buf), NULL, 0,
		NI_NUMERICHOST);
	if (error) {
		return RPyString_FromString("socket.gaierror"); // XXX
	}
	return RPyString_FromString(buf);
}

/* ____________________________________________________________________________ */

RPyString *LL__socket_gethostname(void)
{
	char buf[1024];
	int res;
	res = gethostname(buf, sizeof buf - 1);
	if (res < 0) {
		/* XXX set_error(); */
		RPyRaiseSimpleException(PyExc_socket_error,
					"gethostname() error");
		return NULL;
	}
	buf[sizeof buf - 1] = '\0';
	return RPyString_FromString(buf);
}

struct RPyOpaque_ADDRINFO {
	struct addrinfo *info0;
	struct addrinfo *info;
};

struct RPyOpaque_ADDRINFO *LL__socket_getaddrinfo(RPyString *host, RPyString *port, 
						  int family, int socktype, 
						  int proto, int flags) 
{
	struct addrinfo hints;
	struct addrinfo *res0;
	struct RPyOpaque_ADDRINFO *addr;
	int error;
	char *hptr = RPyString_AsString(host);
	char *pptr = RPyString_AsString(port);

	memset(&hints, 0, sizeof(hints));
	hints.ai_family = family;
	hints.ai_socktype = socktype;
	hints.ai_protocol = proto;
	hints.ai_flags = flags;
	error = getaddrinfo(hptr, pptr, &hints, &res0);
	addr = malloc(sizeof (struct RPyOpaque_ADDRINFO));
	addr->info0 = res0;
	addr->info  = res0;
	return addr;
}

RPyString *LL__socket_gethostbyname(RPyString *name)
{
#ifdef ENABLE_IPV6
	struct sockaddr_storage addrbuf;
#else
        struct sockaddr_in addrbuf;
#endif
	if (setipaddr(RPyString_AsString(name), (struct sockaddr *)&addrbuf,  
		      sizeof(addrbuf), AF_INET) < 0)
		return NULL;
	return makeipaddr((struct sockaddr *)&addrbuf,
			  sizeof(struct sockaddr_in));
}

RPySOCKET_ADDRINFO *LL__socket_nextaddrinfo(struct RPyOpaque_ADDRINFO *addr)
{
	struct addrinfo *info = addr->info;

	if( !info )
		return ll__socket_addrinfo(0,0,0,NULL,NULL,0,0,0);

	addr->info = addr->info->ai_next;

	{
		RPySOCKET_ADDRINFO *ret;
		struct sockaddr_in *a = (struct sockaddr_in *)info->ai_addr;

		RPyString *canonname = RPyString_FromString(
			info->ai_canonname?info->ai_canonname:"");
		RPyString *ipaddr = makeipaddr(info->ai_addr,
					       sizeof(struct sockaddr_in));

		ret = ll__socket_addrinfo(info->ai_family,
					  info->ai_socktype,
					  info->ai_protocol,
					  canonname,
					  ipaddr, // XXX AF_INET Only!
					  ntohs(a->sin_port),0,0);
#if !defined(USING_BOEHM_GC) && !defined(USING_NO_GC)
		canonname->refcount--;
		ipaddr->refcount--;
#endif
		return ret;
	}
}

void LL__socket_freeaddrinfo(struct RPyOpaque_ADDRINFO *addr)
{
	freeaddrinfo(addr->info0);
	free(addr);
}

#ifndef HAVE_INET_PTON

/* Simplistic emulation code for inet_pton that only works for IPv4 */
/* These are not exposed because they do not set errno properly */

int
inet_pton(int af, const char *src, void *dst)
{
	if (af == AF_INET) {
		long packed_addr;
		packed_addr = inet_addr(src);
		if (packed_addr == INADDR_NONE)
			return 0;
		memcpy(dst, &packed_addr, 4);
		return 1;
	}
	/* Should set errno to EAFNOSUPPORT */
	return -1;
}

const char *
inet_ntop(int af, const void *src, char *dst, socklen_t size)
{
	if (af == AF_INET) {
		struct in_addr packed_addr;
		if (size < 16)
			/* Should set errno to ENOSPC. */
			return NULL;
		memcpy(&packed_addr, src, sizeof(packed_addr));
		return strncpy(dst, inet_ntoa(packed_addr), size);
	}
	/* Should set errno to EAFNOSUPPORT */
	return NULL;
}

#endif /* !HAVE_INET_PTON */

#endif /* PYPY_NOT_MAIN_FILE */

#endif /* isolate */
