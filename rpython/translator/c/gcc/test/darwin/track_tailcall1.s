_pypy_g_call__Type:
	subl	$92, %esp
	movl	%ebx, 76(%esp)
	movl	%esi, 80(%esp)
	movl	%edi, 84(%esp)
	movl	%ebp, 88(%esp)
	call	L12381
"L00000000489$pb":
L12381:
	popl	%ebx
	movl	96(%esp), %esi
	movl	100(%esp), %edi
L12333:
	movl	L_pypy_g_pypy_objspace_std_typeobject_W_TypeObject_25$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	%eax, 28(%esp)
	cmpl	%eax, %esi
	je	L12334
	movl	%esi, %ebp
L12336:
	movl	416(%ebp), %eax
	testl	%eax, %eax
	je	L12337
L12338:
	movl	%edi, 8(%esp)
	movl	%ebp, 4(%esp)
	movl	%eax, (%esp)
	call	L_pypy_g_ObjSpace_call_obj_args$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %edi}
	movl	%edi, %edx
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %ecx
	/* GCROOT %edx */
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %esi
	movl	(%esi), %esi
	testl	%esi, %esi
	je	L12378
L12339:
	xorl	%eax, %eax
L12346:
	movl	76(%esp), %ebx
	movl	80(%esp), %esi
	movl	84(%esp), %edi
	movl	88(%esp), %ebp
	addl	$92, %esp
	ret
	.align 4,0x90
L12378:
	movl	%edx, %edi
	movl	%eax, %esi
L12341:
	movl	L_pypy_g_rpy_string_154$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	%eax, 4(%esp)
	movl	%esi, (%esp)
	call	L_pypy_g_lookup____init__$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %esi, %edi}
	movl	%edi, %edx
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %ecx
	/* GCROOT %edx */
	/* GCROOT %esi */
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %ecx
	movl	(%ecx), %ecx
	testl	%ecx, %ecx
	jne	L12339
L12342:
	movl	%edx, 8(%esp)
	movl	%esi, 4(%esp)
	movl	%eax, (%esp)
	call	L_pypy_g_get_and_call_args$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %esi}
	movl	%eax, %edx
	movl	%esi, %eax
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %ecx
	/* GCROOT %eax */
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %esi
	movl	(%esi), %ebp
	testl	%ebp, %ebp
	jne	L12339
L12343:
	cmpl	L_pypy_g_pypy_objspace_std_noneobject_W_NoneObject$non_lazy_ptr-"L00000000489$pb"(%ebx), %edx
	je	L12346
L12344:
	movl	L_pypy_g_pypy_rpython_memory_gc_hybrid_HybridGC$non_lazy_ptr-"L00000000489$pb"(%ebx), %esi
	movl	112(%esi), %edx
	movl	124(%esi), %eax
	subl	%edx, %eax
	cmpl	$19, %eax
	jle	L12347
	movl	%edx, %ecx
L12349:
	movl	$4, (%ecx)
	leal	20(%ecx), %eax
	movl	%eax, 112(%esi)
L12350:
	movl	L_pypy_g_pypy_interpreter_error_OperationError_vtable$non_lazy_ptr-"L00000000489$pb"(%ebx), %edx
	movl	%edx, 4(%ecx)
	movl	L_pypy_g_pypy_objspace_std_typeobject_W_TypeObject$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	%eax, 12(%ecx)
	movl	L_pypy_g_pypy_objspace_std_stringobject_W_StringObject_775$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	%eax, 16(%ecx)
	movl	$0, 8(%ecx)
L12351:
	movl	%ecx, 4(%esp)
	movl	%edx, (%esp)
	call	L_pypy_g_RPyRaiseException$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | }
	xorl	%eax, %eax
	jmp	L12346
	.align 4,0x90
L12337:
	movl	L_pypy_g_rpy_string_211$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	%eax, 4(%esp)
	movl	%ebp, (%esp)
	call	L_pypy_g_W_TypeObject_lookup_where_with_method_cache$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %edi, %ebp}
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %edx
	/* GCROOT %ebp */
	/* GCROOT %edi */
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %ecx
	movl	(%ecx), %esi
	testl	%esi, %esi
	jne	L12339
L12353:
	movl	4(%eax), %esi
	movl	$0, 8(%esp)
	movl	%ebp, 4(%esp)
	movl	8(%eax), %eax
	movl	%eax, (%esp)
	call	L_pypy_g_get$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %esi, %edi, %ebp}
	movl	%eax, 36(%esp)
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	/* GCROOT %ebp */
	/* GCROOT %edi */
	movl	%edi, 40(%esp)
	movl	%esi, %eax
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %edx
	/* GCROOT %eax */
	movl	%esi, %edx
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %ecx
	/* GCROOT %edx */
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %esi
	movl	(%esi), %ecx
	testl	%ecx, %ecx
	jne	L12339
L12354:
	testl	%eax, %eax
	je	L12356
L12355:
	movl	4(%eax), %eax
	movl	(%eax), %eax
	cmpl	$623, %eax
	jle	L12356
L12367:
	cmpl	$629, %eax
	jg	L12356
L12368:
	testb	$2, 9(%edx)
	jne	L12356
L12369:
	cmpl	28(%esp), %edx
	je	L12356
L12370:
	testb	$8, 2(%ebp)
	je	L12372
L12371:
	movl	36(%esp), %eax
	movl	%eax, 4(%esp)
	movl	%ebp, (%esp)
	call	L_pypy_g_remember_young_pointer$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %ebp, 40(%esp)}
L12372:
	movl	36(%esp), %esi
	movl	%esi, 416(%ebp)
L12356:
	movl	40(%esp), %eax
	movl	%eax, 8(%esp)
	movl	%ebp, 4(%esp)
	movl	36(%esp), %edx
	movl	%edx, (%esp)
	call	L_pypy_g_ObjSpace_call_obj_args$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %ebp, 40(%esp)}
	movl	%eax, %edi
	movl	%ebp, %esi
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %ecx
	/* GCROOT %esi */
	movl	%esi, 44(%esp)
	movl	40(%esp), %eax
	/* GCROOT %eax */
	movl	%eax, 48(%esp)
	movl	%ebp, %esi
	/* GCROOT %esi */
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %edx
	movl	(%edx), %eax
	testl	%eax, %eax
	jne	L12339
L12357:
	movl	4(%edi), %eax
	movl	%edi, (%esp)
	call	*32(%eax)
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %edi, 48(%esp)}
	/* keepalive %eax */
	/* keepalive 44(%esp) */
	movl	%esi, 4(%esp)
	movl	%eax, (%esp)
	call	L_pypy_g___mm_issubtype_perform_call$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %edi, 48(%esp)}
	movl	%eax, %esi
	movl	%edi, %ebp
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %ecx
	/* GCROOT %ebp */
	movl	48(%esp), %edi
	/* GCROOT %edi */
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	(%eax), %eax
	testl	%eax, %eax
	jne	L12339
L12358:
	movl	%esi, (%esp)
	call	L_pypy_g___mm_nonzero_0_perform_call$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %esi, %edi, %ebp}
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %edx
	/* GCROOT %ebp */
	movl	%ebp, 52(%esp)
	movl	%ebp, %ecx
	/* GCROOT %edi */
	movl	%edi, 56(%esp)
	/* GCROOT %esi */
	movl	%esi, 60(%esp)
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %esi
	movl	(%esi), %ebp
	testl	%ebp, %ebp
	je	L12379
L12359:
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	4(%eax), %esi
	movl	$0, 4(%eax)
	movl	$0, (%eax)
	/* keepalive %esi */
	/* keepalive 60(%esp) */
	/* keepalive 52(%esp) */
	/* keepalive 56(%esp) */
	movl	L_pypy_g_pypy_objspace_std_multimethod_FailedToImplement_$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	%eax, 4(%esp)
	movl	%ebp, (%esp)
	call	L_pypy_g_ll_issubclass__object_vtablePtr_object_vtablePtr$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | 52(%esp), 56(%esp)}
	movl	%ebp, %edx
	movl	%esi, %ecx
	testb	%al, %al
	je	L12351
L12364:
	movl	60(%esp), %edx
	movl	%edx, (%esp)
	call	L_pypy_g_is_true$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | 52(%esp), 56(%esp)}
	movl	%eax, %esi
	movl	52(%esp), %eax
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %ecx
	/* GCROOT %eax */
	movl	56(%esp), %edx
	/* GCROOT %edx */
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %ecx
	movl	(%ecx), %ecx
	testl	%ecx, %ecx
	jne	L12339
	movl	%eax, %ecx
	movl	%edx, %edi
	movl	%esi, %edx
L12361:
	movl	%ecx, %eax
	movl	%ecx, %esi
	testb	%dl, %dl
	jne	L12341
	jmp	L12346
	.align 4,0x90
L12334:
	movl	$1, 8(%esp)
	movl	%edi, 4(%esp)
	movl	4(%edi), %eax
	movsbl	22(%eax),%eax
	movl	%eax, (%esp)
	call	L_pypy_g_dispatcher_60$stub
	;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %esi, %edi}
	movl	%esi, %ecx
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %edx
	/* GCROOT %ecx */
	movl	%ecx, %ebp
	movl	%edi, %edx
	movl	L___gcmapend$non_lazy_ptr-"L00000000489$pb"(%ebx), %esi
	/* GCROOT %edx */
	movl	%edx, %edi
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %esi
	movl	(%esi), %esi
	movl	%esi, 32(%esp)
	testl	%esi, %esi
	je	L12380
L12373:
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	4(%eax), %esi
	movl	$0, 4(%eax)
	movl	$0, (%eax)
	/* keepalive %esi */
	/* keepalive %edx */
	/* keepalive %ecx */
	movl	L_pypy_g_exceptions_ValueError_vtable$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	%eax, 4(%esp)
	movl	32(%esp), %edx
	movl	%edx, (%esp)
	call	L_pypy_g_ll_issubclass__object_vtablePtr_object_vtablePtr$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | %edi, %ebp}
	movl	32(%esp), %edx
	movl	%esi, %ecx
	testb	%al, %al
	je	L12351
	jmp	L12336
L12380:
L12374:
	cmpl	$1, 4(%eax)
	jne	L12336
L12375:
	movl	8(%eax), %eax
	movl	4(%eax), %edx
	movl	%eax, 96(%esp)
	movl	32(%edx), %ecx
	movl	76(%esp), %ebx
	movl	80(%esp), %esi
	movl	84(%esp), %edi
	movl	88(%esp), %ebp
	addl	$92, %esp
	jmp	*%ecx
L12347:
	movl	%esi, (%esp)
	call	L_pypy_g_GenerationGC_collect_nursery$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | }
	movl	%eax, %ecx
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000489$pb"(%ebx), %eax
	movl	(%eax), %edi
	testl	%edi, %edi
	jne	L12339
	jmp	L12349
L12379:
L12360:
	movzbl	8(%eax), %edx
	jmp	L12361
	.align 4,0x90
