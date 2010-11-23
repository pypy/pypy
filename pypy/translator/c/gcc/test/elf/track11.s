	.type	pypy_g_f_gc_set_max_heap_size, @function
pypy_g_f_gc_set_max_heap_size:
	;; This really occurred in real-life (see around r77794).
	;; This function is large, but actually in all paths it
	;; will soon hit a RPyAssertFailed and abort.
.L22962:
.L22963:
.L22964:
	pushl	%ebp
	movl	$pypy_g_exceptions_NotImplementedError_vtable, %eax
	pushl	%edi
	pushl	%esi
	pushl	%ebx
	subl	$28, %esp
	cmpl	$pypy_g_py__code_assertion_AssertionError_vtable, %eax
	je	.L23136
.L22965:
.L22967:
.L22969:
.L22971:
.L22972:
.L22974:
	movl	$.LC1, (%esp)
	movl	$.LC2, %ebp
	movl	$__FUNCTION__.1761, %esi
	movl	%ebp, 12(%esp)
	movl	$726, %edi
	movl	$loc.982, %ebp
	movl	%esi, 8(%esp)
	xorl	%esi, %esi
	movl	$pypy_g_exceptions_NotImplementedError_vtable, %ebx
	movl	%edi, 4(%esp)
	call	RPyAssertFailed
	movl	%ebx, pypy_g_ExcData
	movl	pypydtcount, %edi
	xorl	%edx, %edx
	movl	$400000, (%esp)
	movl	$pypy_g_exceptions_NotImplementedError_vtable, %eax
	movl	$pypy_g_exceptions_NotImplementedError, %ecx
	movl	%ecx, pypy_g_ExcData+4
	movl	%edx, pypy_debug_tracebacks(,%edi,8)
	movl	%eax, pypy_debug_tracebacks+4(,%edi,8)
	incl	%edi
	andl	$127, %edi
	movl	%esi, pypy_debug_tracebacks+4(,%edi,8)
	movl	%ebp, pypy_debug_tracebacks(,%edi,8)
	incl	%edi
	andl	$127, %edi
	movl	%edi, pypydtcount
	call	pypy_g_mallocstr__Signed
	movl	pypy_g_ExcData, %ebx
	movl	%eax, %esi
	testl	%ebx, %ebx
	jne	.L22976
.L22977:
	xorl	%ebx, %ebx
	testl	%eax, %eax
	je	.L23117
.L23127:
.L22981:
	movb	$120, 12(%esi,%ebx)
	incl	%ebx
	cmpl	$399999, %ebx
	jle	.L23127
	.p2align 4,,15
.L23112:
	movl	pypy_g_ExcData, %ebx
	movl	%esi, %edi
	testl	%ebx, %ebx
	jne	.L22990
.L22991:
.L22992:
.L22993:
.L23137:
.L22995:
	movl	$4000000, (%esp)
	call	pypy_g_mallocstr__Signed
	movl	pypy_g_ExcData, %ebx
	movl	%eax, %esi
	testl	%ebx, %ebx
	jne	.L22997
.L22998:
	xorl	%ebx, %ebx
	testl	%eax, %eax
	je	.L23120
.L23129:
.L23002:
	movb	$120, 12(%esi,%ebx)
	incl	%ebx
	cmpl	$3999999, %ebx
	jle	.L23129
.L23114:
	movl	pypy_g_ExcData, %ebx
	movl	%esi, %ebp
	jmp	.L23004
.L22980:
	.p2align 4,,7
.L22976:
.L22983:
.L22987:
	movl	pypydtcount, %eax
	xorl	%edx, %edx
	movl	$loc.586, %ecx
	xorl	%edi, %edi
	movl	%ecx, pypy_debug_tracebacks(,%eax,8)
	movl	%edx, pypy_debug_tracebacks+4(,%eax,8)
	incl	%eax
	andl	$127, %eax
	movl	%eax, pypydtcount
	testl	%ebx, %ebx
	je	.L23137
.L22990:
	movl	pypydtcount, %ecx
	movl	$loc.1444, %edx
	movl	pypy_g_ExcData+4, %edi
	movl	%edx, pypy_debug_tracebacks(,%ecx,8)
	movl	%ebx, pypy_debug_tracebacks+4(,%ecx,8)
	incl	%ecx
	andl	$127, %ecx
	movl	%ecx, pypydtcount
	cmpl	$pypy_g_py__code_assertion_AssertionError_vtable, %ebx
	je	.L23075
	cmpl	$pypy_g_exceptions_NotImplementedError_vtable, %ebx
	je	.L23075
.L23074:
.L23076:
	xorl	%eax, %eax
	xorl	%ebp, %ebp
	movl	%eax, pypy_g_ExcData+4
	movl	%ebp, pypy_g_ExcData
#APP
	/* keepalive %edi */
#NO_APP
	testl	%ebx, %ebx
	movl	pypy_g_exceptions_MemoryError_vtable, %esi
	je	.L23138
.L23080:
.L23083:
	movl	(%ebx), %ebp
	movl	pypy_g_exceptions_MemoryError_vtable+4, %edx
	subl	%esi, %ebp
	subl	%esi, %edx
	cmpl	%edx, %ebp
	setb	%cl
#APP
	/* GC_NOCOLLECT pypy_g_ll_issubclass */
#NO_APP
	testb	%cl, %cl
	je	.L23086
	xorl	%edx, %edx
	xorl	%ecx, %ecx
	xorl	%eax, %eax
.L23036:
.L23038:
.L23040:
	testl	%eax, %eax
	movzbl	%dl, %ebp
	setne	%bl
	movzbl	%bl, %esi
	xorl	%eax, %eax
	addl	%esi, %ebp
	testl	%ecx, %ecx
	setne	%al
	leal	(%ebp,%eax), %eax
.L23041:
	addl	$28, %esp
	popl	%ebx
	popl	%esi
	popl	%edi
	popl	%ebp
	ret
	.p2align 4,,7
.L23117:
	call	RPyAbort
	movb	$120, 12(%esi,%ebx)
	incl	%ebx
	cmpl	$399999, %ebx
	jg	.L23112
	call	RPyAbort
	movb	$120, 12(%esi,%ebx)
	incl	%ebx
	cmpl	$399999, %ebx
	jle	.L23117
	jmp	.L23112
.L23075:
	call	pypy_debug_catch_fatal_exception
	jmp	.L23074
.L23138:
	call	RPyAbort
	jmp	.L23080
.L23136:
	movl	$.LC1, (%esp)
	movl	$.LC0, %ebx
	movl	$__FUNCTION__.1761, %ecx
	movl	%ebx, 12(%esp)
	movl	$724, %edx
	movl	%ecx, 8(%esp)
	movl	%edx, 4(%esp)
	call	RPyAssertFailed
	jmp	.L22965
.L23001:
.L22997:
	movl	pypydtcount, %ebp
	movl	$loc.586, %eax
	xorl	%esi, %esi
	movl	%eax, pypy_debug_tracebacks(,%ebp,8)
	movl	%esi, pypy_debug_tracebacks+4(,%ebp,8)
	incl	%ebp
	andl	$127, %ebp
	movl	%ebp, pypydtcount
	xorl	%ebp, %ebp
.L23004:
.L23008:
	movl	%edi, %esi
#APP
	/* GCROOT %esi */
#NO_APP
	movl	%esi, 24(%esp)
	testl	%ebx, %ebx
	je	.L23139
.L23011:
	movl	pypydtcount, %ecx
	movl	$loc.1443, %edx
	movl	pypy_g_ExcData+4, %edi
	movl	%edx, pypy_debug_tracebacks(,%ecx,8)
	movl	%ebx, pypy_debug_tracebacks+4(,%ecx,8)
	incl	%ecx
	andl	$127, %ecx
	movl	%ecx, pypydtcount
	cmpl	$pypy_g_py__code_assertion_AssertionError_vtable, %ebx
	je	.L23059
	cmpl	$pypy_g_exceptions_NotImplementedError_vtable, %ebx
	je	.L23059
.L23058:
.L23060:
	xorl	%ebp, %ebp
	xorl	%eax, %eax
	movl	%ebp, pypy_g_ExcData+4
	movl	%eax, pypy_g_ExcData
#APP
	/* keepalive %edi */
	/* keepalive %esi */
#NO_APP
	testl	%ebx, %ebx
	movl	pypy_g_exceptions_MemoryError_vtable, %esi
	je	.L23140
.L23064:
.L23067:
	movl	(%ebx), %eax
	xorl	%ecx, %ecx
	movl	pypy_g_exceptions_MemoryError_vtable+4, %ebp
	subl	%esi, %eax
	subl	%esi, %ebp
	xorl	%esi, %esi
	cmpl	%ebp, %eax
	setb	%dl
#APP
	/* GC_NOCOLLECT pypy_g_ll_issubclass */
#NO_APP
	testb	%dl, %dl
	je	.L23141
.L23033:
.L23034:
	movl	24(%esp), %ebx
	movb	$1, %dl
	testl	%ebx, %ebx
	je	.L23142
	movl	%esi, %eax
	jmp	.L23036
.L23086:
.L23087:
.L23088:
	movl	%edi, pypy_g_ExcData+4
	movl	pypydtcount, %esi
	movl	$-1, %edi
	movl	%ebx, pypy_g_ExcData
	movl	%edi, pypy_debug_tracebacks(,%esi,8)
	movl	%ebx, pypy_debug_tracebacks+4(,%esi,8)
	incl	%esi
	andl	$127, %esi
	movl	%esi, pypydtcount
#APP
	/* GC_NOCOLLECT pypy_g_RPyReRaiseException */
#NO_APP
	movl	$-1, %eax
	jmp	.L23041
	.p2align 4,,7
.L23120:
	call	RPyAbort
	movb	$120, 12(%esi,%ebx)
	incl	%ebx
	cmpl	$3999999, %ebx
	jg	.L23114
	call	RPyAbort
	movb	$120, 12(%esi,%ebx)
	incl	%ebx
	cmpl	$3999999, %ebx
	jle	.L23120
	jmp	.L23114
.L23142:
	xorl	%edx, %edx
	movl	%esi, %eax
	jmp	.L23036
.L23059:
	call	pypy_debug_catch_fatal_exception
	jmp	.L23058
.L23140:
	call	RPyAbort
	jmp	.L23064
.L23012:
.L23013:
.L23014:
.L23139:
.L23016:
	movl	$40000000, (%esp)
	call	pypy_g_mallocstr__Signed
	movl	pypy_g_ExcData, %ebx
	movl	%eax, %edi
	testl	%ebx, %ebx
	jne	.L23018
.L23019:
	xorl	%ebx, %ebx
	testl	%eax, %eax
	je	.L23123
.L23131:
.L23023:
	movb	$120, 12(%edi,%ebx)
	incl	%ebx
	cmpl	$39999999, %ebx
	jle	.L23131
.L23116:
	movl	pypy_g_ExcData, %ebx
	movl	%edi, %eax
.L23025:
.L23029:
#APP
	/* GCROOT %esi */
#NO_APP
	movl	%esi, 24(%esp)
	movl	%ebp, %edi
#APP
	/* GCROOT %edi */
#NO_APP
	testl	%ebx, %ebx
	jne	.L23032
	movl	%eax, %ecx
	movl	%edi, %esi
	jmp	.L23033
.L23123:
	call	RPyAbort
	movb	$120, 12(%edi,%ebx)
	incl	%ebx
	cmpl	$39999999, %ebx
	jle	.L23123
	jmp	.L23116
.L23022:
.L23018:
	movl	pypydtcount, %ecx
	movl	$loc.586, %edx
	xorl	%edi, %edi
	xorl	%eax, %eax
	movl	%edx, pypy_debug_tracebacks(,%ecx,8)
	movl	%edi, pypy_debug_tracebacks+4(,%ecx,8)
	incl	%ecx
	andl	$127, %ecx
	movl	%ecx, pypydtcount
	jmp	.L23025
.L23141:
.L23070:
.L23071:
.L23072:
	movl	%edi, pypy_g_ExcData+4
	movl	pypydtcount, %esi
	movl	$-1, %edi
	movl	%ebx, pypy_g_ExcData
	movl	%edi, pypy_debug_tracebacks(,%esi,8)
	movl	%ebx, pypy_debug_tracebacks+4(,%esi,8)
	incl	%esi
	andl	$127, %esi
	movl	%esi, pypydtcount
#APP
	/* GC_NOCOLLECT pypy_g_RPyReRaiseException */
#NO_APP
	movl	$-1, %eax
	jmp	.L23041
.L23032:
	movl	pypydtcount, %ecx
	movl	$loc.1442, %edx
	movl	pypy_g_ExcData+4, %ebp
	movl	%edx, pypy_debug_tracebacks(,%ecx,8)
	movl	%ebx, pypy_debug_tracebacks+4(,%ecx,8)
	incl	%ecx
	andl	$127, %ecx
	movl	%ecx, pypydtcount
	cmpl	$pypy_g_py__code_assertion_AssertionError_vtable, %ebx
	je	.L23043
	cmpl	$pypy_g_exceptions_NotImplementedError_vtable, %ebx
	je	.L23043
.L23042:
.L23044:
	xorl	%ecx, %ecx
	xorl	%eax, %eax
	movl	%ecx, pypy_g_ExcData+4
	movl	%eax, pypy_g_ExcData
#APP
	/* keepalive %ebp */
	/* keepalive %esi */
	/* keepalive %edi */
#NO_APP
	testl	%ebx, %ebx
	movl	pypy_g_exceptions_MemoryError_vtable, %esi
	je	.L23143
.L23048:
.L23051:
	movl	(%ebx), %eax
	xorl	%ecx, %ecx
	movl	pypy_g_exceptions_MemoryError_vtable+4, %edx
	subl	%esi, %eax
	subl	%esi, %edx
	cmpl	%edx, %eax
	movl	%edi, %esi
	setb	%dl
#APP
	/* GC_NOCOLLECT pypy_g_ll_issubclass */
#NO_APP
	testb	%dl, %dl
	jne	.L23033
.L23054:
.L23055:
.L23056:
	movl	%ebp, pypy_g_ExcData+4
	movl	pypydtcount, %edi
	movl	$-1, %ebp
	movl	%ebx, pypy_g_ExcData
	movl	%ebp, pypy_debug_tracebacks(,%edi,8)
	movl	%ebx, pypy_debug_tracebacks+4(,%edi,8)
	incl	%edi
	andl	$127, %edi
	movl	%edi, pypydtcount
#APP
	/* GC_NOCOLLECT pypy_g_RPyReRaiseException */
#NO_APP
	movl	$-1, %eax
	jmp	.L23041
.L23043:
	call	pypy_debug_catch_fatal_exception
	jmp	.L23042
.L23143:
	call	RPyAbort
	jmp	.L23048
	.size	pypy_g_f_gc_set_max_heap_size, .-pypy_g_f_gc_set_max_heap_size
