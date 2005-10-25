
#ifdef MS_WINDOWS
  /* winsock2.h has already been included before windows.h in thread_nt.h */
#else
# include <arpa/inet.h>
# include <sys/types.h>
# include <sys/socket.h>
# include <netdb.h>
#endif

int LL__socket_ntohs(int htons);
int LL__socket_htons(int ntohs);
long LL__socket_ntohl(long htonl);
long LL__socket_htonl(long ntohl);
RPyString *LL__socket_gethostname(void);
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

RPyString *LL__socket_gethostname(void)
{
	char buf[1024];
	int res;
	res = gethostname(buf, sizeof buf - 1);
	if (res < 0) {
		//XXX
		//RPYTHON_RAISE_OSERROR(errno);
		RPyRaiseSimpleException(PyExc_ValueError,
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

RPyString *makeipaddr(struct sockaddr *addr)
{
	char buf[NI_MAXHOST];
	int error;

	error = getnameinfo(addr, sizeof (struct sockaddr), buf, sizeof(buf), NULL, 0,
		NI_NUMERICHOST);
	if (error) {
		return RPyString_FromString("Error"); // XXX
	}
	return RPyString_FromString(buf);
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
		RPyString *ipaddr = makeipaddr(info->ai_addr);

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
