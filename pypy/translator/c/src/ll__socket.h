
#ifdef MS_WINDOWS
# pragma comment(lib, "ws2_32.lib")
#else
# include <arpa/inet.h>
#endif

int LL__socket_ntohs(int htons);
int LL__socket_htons(int ntohs);
long LL__socket_ntohl(long htonl);
long LL__socket_htonl(long ntohl);
struct RPyOpaque_ADDRINFO *LL__socket_getaddrinfo(RPyString *host, RPyString *port, 
						  int family, int socktype, 
						  int proto, int flags);
RPySOCKET_ADDRINFO *LL__socket_nextaddrinfo(struct RPyOpaque_ADDRINFO *addr);

#ifndef PYPY_NOT_MAIN_FILE
#ifdef MS_WINDOWS
# include <Ws2tcpip.h>
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

RPyString *LL__socket_gethostname()
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
		// XXX DECREF(canonname)
		// XXX DECREF(ipaddr)
	}
}

void LL__socket_freeaddrinfo(struct RPyOpaque_ADDRINFO *addr)
{
	freeaddrinfo(addr->info0);
	free(addr2);
}
#endif
