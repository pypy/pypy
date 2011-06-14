PUBLIC	??_C@_0BN@BIPHFGBC@pypy_g_ll_math_ll_math_frexp?$AA@ ; `string'
PUBLIC	_pypy_g_ll_math_ll_math_frexp
;	COMDAT ??_C@_0BN@BIPHFGBC@pypy_g_ll_math_ll_math_frexp?$AA@
CONST	SEGMENT
??_C@_0BN@BIPHFGBC@pypy_g_ll_math_ll_math_frexp?$AA@ DB 'pypy_g_ll_math_l'
	DB	'l_math_frexp', 00H				; `string'
; Function compile flags: /Ogtpy
CONST	ENDS
;	COMDAT _pypy_g_ll_math_ll_math_frexp
_TEXT	SEGMENT
_l_mantissa_0$ = -8					; size = 8
_l_v21638$ = -8						; size = 8
_l_x_14$ = 8						; size = 8
_pypy_g_ll_math_ll_math_frexp PROC			; COMDAT

; 58245: struct pypy_tuple2_0 *pypy_g_ll_math_ll_math_frexp(double l_x_14) {

	push	ebp
	mov	ebp, esp
	and	esp, -64				; ffffffc0H

; 58246: 	long *l_exp_p_0; double l_mantissa_0; bool_t l_v21641;
; 58247: 	bool_t l_v21643; bool_t l_v21644; bool_t l_v21646; bool_t l_v21647;
; 58248: 	bool_t l_v21652; bool_t l_v21653; bool_t l_v21660; bool_t l_v21666;
; 58249: 	bool_t l_v21670; bool_t l_v21674; bool_t l_v21676; double l_v21638;
; 58250: 	long l_v21637; long l_v21649; long l_v21651; long l_v21677;
; 58251: 	long l_v21678; struct pypy_exceptions_Exception0 *l_v21687;
; 58252: 	struct pypy_header0 *l_v21654; struct pypy_object0 *l_v21682;
; 58253: 	struct pypy_object0 *l_v21691; struct pypy_object_vtable0 *l_v21665;
; 58254: 	struct pypy_object_vtable0 *l_v21669;
; 58255: 	struct pypy_object_vtable0 *l_v21675;
; 58256: 	struct pypy_object_vtable0 *l_v21683; struct pypy_tuple2_0 *l_v21640;
; 58257: 	struct pypy_tuple2_0 *l_v21695; void* l_v21639; void* l_v21648;
; 58258: 	void* l_v21650; void* l_v21656; void* l_v21658; void* l_v21659;
; 58259: 	void* l_v21668; void* l_v21672; void* l_v21679; void* l_v21688;
; 58260: 	void* l_v21696;
; 58261: 	goto block0;
; 58262: 
; 58263:     block0:
; 58264: 	l_v21641 = pypy_g_ll_math_ll_math_isnan(l_x_14);

	fld	QWORD PTR _l_x_14$[ebp]
	sub	esp, 52					; 00000034H
	push	ebx
	push	esi
	push	edi
	sub	esp, 8
	fstp	QWORD PTR [esp]
$block0$88239:
	call	_pypy_g_ll_math_ll_math_isnan

; 58265: 	pypy_asm_gc_nocollect(pypy_g_ll_math_ll_math_isnan);
; 58266: 	l_v21643 = l_v21641;
; 58267: 	if (l_v21643) {
; 58268: 		l_v21637 = 0L;
; 58269: 		l_v21638 = l_x_14;

	fld	QWORD PTR _l_x_14$[ebp]
	add	esp, 8
	test	al, al

; 58270: 		goto block3;

	jne	SHORT $LN10@pypy_g_ll_@159

; 58271: 	}
; 58272: 	goto block1;
; 58273: 
; 58274:     block1:
; 58275: 	l_v21644 = pypy_g_ll_math_ll_math_isinf(l_x_14);

	sub	esp, 8
	fstp	QWORD PTR [esp]
$block1$88243:
	call	_pypy_g_ll_math_ll_math_isinf
	add	esp, 8

; 58276: 	pypy_asm_gc_nocollect(pypy_g_ll_math_ll_math_isinf);
; 58277: 	l_v21646 = l_v21644;
; 58278: 	if (l_v21646) {

	test	al, al
	je	SHORT $block2$88245

; 58279: 		l_v21637 = 0L;
; 58280: 		l_v21638 = l_x_14;

	fld	QWORD PTR _l_x_14$[ebp]
$LN10@pypy_g_ll_@159:

; 58288: 		goto block14;
; 58289: 	}
; 58290: 	l_v21637 = 0L;

	xor	edi, edi
$LN30@pypy_g_ll_@159:

; 58291: 	l_v21638 = l_x_14;
; 58292: 	goto block3;
; 58293: 
; 58294:     block3:
; 58295: 	l_v21648 = (&pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC)->ssgc_inst_free;

	mov	esi, DWORD PTR _pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+4
	fstp	QWORD PTR _l_v21638$[esp+64]

; 58296: 	OP_RAW_MALLOC_USAGE((0 + ROUND_UP_FOR_ALLOCATION(sizeof(struct pypy_tuple2_0), sizeof(struct pypy_forwarding_stub0))), l_v21649);
; 58297: 	l_v21650 = (&pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC)->ssgc_inst_top_of_space;
; 58298: 	OP_ADR_DELTA(l_v21650, l_v21648, l_v21651);

	mov	eax, DWORD PTR _pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12
	sub	eax, esi

; 58299: 	OP_INT_GT(l_v21649, l_v21651, l_v21652);

	cmp	eax, 24					; 00000018H
$block3$88242:

; 58300: 	if (l_v21652) {

	jge	$block4$88260

; 58334: 	l_v21695 = l_v21640;
; 58335: 	goto block8;
; 58336: 
; 58337:     block8:
; 58338: 	RPY_DEBUG_RETURN();
; 58339: 	return l_v21695;
; 58340: 
; 58341:     block9:
; 58342: 	PYPY_DEBUG_RECORD_TRACEBACK("ll_math_ll_math_frexp");
; 58343: 	l_v21695 = ((struct pypy_tuple2_0 *) NULL);
; 58344: 	goto block8;
; 58345: 
; 58346:     block10:
; 58347: 	abort();  /* debug_llinterpcall should be unreachable */
; 58348: 	l_v21665 = (&pypy_g_ExcData)->ed_exc_type;
; 58349: 	l_v21666 = (l_v21665 == NULL);
; 58350: 	if (!l_v21666) {
; 58351: 		goto block11;
; 58352: 	}
; 58353: 	goto block5;
; 58354: 
; 58355:     block11:
; 58356: 	PYPY_DEBUG_RECORD_TRACEBACK("ll_math_ll_math_frexp");
; 58357: 	l_v21696 = NULL;
; 58358: 	goto block6;
; 58359: 
; 58360:     block12:
; 58361: 	l_v21668 = pypy_g_SemiSpaceGC_obtain_free_space((&pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC), (0 + ROUND_UP_FOR_ALLOCATION(sizeof(struct pypy_tuple2_0), sizeof(struct pypy_forwarding_stub0))));

	push	24					; 00000018H
	push	OFFSET _pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC
$block12$88259:
	call	_pypy_g_SemiSpaceGC_obtain_free_space
    ;; expected {4(%ebp) | 16(%esp), 12(%esp), 8(%esp), (%ebp) | }

; 58362: 	l_v21669 = (&pypy_g_ExcData)->ed_exc_type;
; 58363: 	l_v21670 = (l_v21669 == NULL);

	xor	ecx, ecx
	add	esp, 8
	cmp	DWORD PTR _pypy_g_ExcData, ecx

; 58364: 	if (!l_v21670) {

	je	$LN5@pypy_g_ll_@159

; 58368: 	goto block4;
; 58369: 
; 58370:     block13:
; 58371: 	PYPY_DEBUG_RECORD_TRACEBACK("ll_math_ll_math_frexp");

	mov	eax, DWORD PTR _pypydtcount
	mov	DWORD PTR _pypy_debug_tracebacks[eax*8], OFFSET ?loc@?N@??pypy_g_ll_math_ll_math_frexp@@9@9
	mov	DWORD PTR _pypy_debug_tracebacks[eax*8+4], ecx
	inc	eax
	and	eax, 8191				; 00001fffH
	mov	DWORD PTR _pypy_debug_tracebacks[eax*8], OFFSET ?loc@?8??pypy_g_ll_math_ll_math_frexp@@9@9
	mov	DWORD PTR _pypy_debug_tracebacks[eax*8+4], ecx
	inc	eax
	and	eax, 8191				; 00001fffH
	mov	DWORD PTR _pypydtcount, eax
$block13$88313:
$block9$88285:
	xor	eax, eax

; 58423: 	goto block8;
; 58424: }

	pop	edi
	pop	esi
	pop	ebx
	mov	esp, ebp
	pop	ebp
	ret	0
$block2$88245:

; 58281: 		goto block3;
; 58282: 	}
; 58283: 	goto block2;
; 58284: 
; 58285:     block2:
; 58286: 	OP_FLOAT_IS_TRUE(l_x_14, l_v21647);

	fldz
	fld	QWORD PTR _l_x_14$[ebp]
	fucom	ST(1)
	fnstsw	ax
	fstp	ST(1)
	test	ah, 68					; 00000044H

; 58287: 	if (l_v21647) {

	jnp	$LN10@pypy_g_ll_@159

; 58372: 	l_v21696 = NULL;
; 58373: 	goto block6;
; 58374: 
; 58375:     block14:
; 58376: 	l_v21672 = pypy_g__ll_malloc_varsize_no_length__Signed_Signed_Sign(1L, (0 + 0), sizeof(long));

	push	4
	fstp	ST(0)
	push	0
	push	1
$block14$88247:
	call	_pypy_g__ll_malloc_varsize_no_length__Signed_Signed_Sign
    ;; expected {4(%ebp) | 20(%esp), 16(%esp), 12(%esp), (%ebp) | }
	mov	esi, eax

; 58377: 	OP_TRACK_ALLOC_START(l_v21672, /* nothing */);

	push	OFFSET ??_C@_0BN@BIPHFGBC@pypy_g_ll_math_ll_math_frexp?$AA@
	push	esi
	call	_pypy_debug_alloc_start
    ;; expected {4(%ebp) | 28(%esp), 24(%esp), 20(%esp), (%ebp) | }
	add	esp, 20					; 00000014H

; 58378: 	l_exp_p_0 = (long *)l_v21672;
; 58379: 	l_v21674 = (l_exp_p_0 != NULL);

	test	esi, esi

; 58380: 	if (!l_v21674) {

	jne	SHORT $block15$88324

; 58418: 	goto block8;
; 58419: 
; 58420:     block18:
; 58421: 	PYPY_DEBUG_RECORD_TRACEBACK("ll_math_ll_math_frexp");

	mov	eax, DWORD PTR _pypydtcount
	mov	DWORD PTR _pypy_debug_tracebacks[eax*8], OFFSET ?loc@?BB@??pypy_g_ll_math_ll_math_frexp@@9@9
	mov	DWORD PTR _pypy_debug_tracebacks[eax*8+4], esi
	inc	eax
	and	eax, 8191				; 00001fffH
	mov	DWORD PTR _pypydtcount, eax
$block18$88323:

; 58422: 	l_v21695 = ((struct pypy_tuple2_0 *) NULL);

	xor	eax, eax

; 58423: 	goto block8;
; 58424: }

	pop	edi
	pop	esi
	pop	ebx
	mov	esp, ebp
	pop	ebp
	ret	0
$block15$88324:

; 58381: 		goto block18;
; 58382: 	}
; 58383: 	goto block15;
; 58384: 
; 58385:     block15:
; 58386: 	l_mantissa_0 = pypy_g_frexp__Float_arrayPtr_star_2(l_x_14, l_exp_p_0);

	fld	QWORD PTR _l_x_14$[ebp]
	push	esi
	sub	esp, 8
	fstp	QWORD PTR [esp]
	call	_pypy_g_frexp__Float_arrayPtr_star_2
    ;; expected {4(%ebp) | 20(%esp), 16(%esp), 12(%esp), (%ebp) | }

; 58387: 	l_v21675 = (&pypy_g_ExcData)->ed_exc_type;
; 58388: 	l_v21676 = (l_v21675 == NULL);

	mov	edi, DWORD PTR _pypy_g_ExcData
	fstp	QWORD PTR _l_mantissa_0$[esp+76]
	add	esp, 12					; 0000000cH
	test	edi, edi

; 58389: 	if (!l_v21676) {

	je	SHORT $block16$88328

; 58403: 
; 58404:     block17:
; 58405: 	l_v21682 = (&pypy_g_ExcData)->ed_exc_value;
; 58406: 	l_v21683 = (&pypy_g_ExcData)->ed_exc_type;
; 58407: 	PYPY_DEBUG_CATCH_EXCEPTION("ll_math_ll_math_frexp", l_v21683, l_v21683 == (&pypy_g_py__code_assertion_AssertionError_vtable.ae_super.ae_super.se_super.e_super) || l_v21683 == (&pypy_g_exceptions_NotImplementedError_vtable.nie_super.re_super.se_super.e_super));

	mov	eax, DWORD PTR _pypydtcount
	mov	ebx, DWORD PTR _pypy_g_ExcData+4
	mov	DWORD PTR _pypy_debug_tracebacks[eax*8], OFFSET ?loc@?BA@??pypy_g_ll_math_ll_math_frexp@@9@9
	mov	DWORD PTR _pypy_debug_tracebacks[eax*8+4], edi
	inc	eax
	and	eax, 8191				; 00001fffH
$block17$88327:
	mov	DWORD PTR _pypydtcount, eax
	cmp	edi, OFFSET _pypy_g_py__code_assertion_AssertionError_vtable
	je	SHORT $LN1@pypy_g_ll_@159
	cmp	edi, OFFSET _pypy_g_exceptions_NotImplementedError_vtable
	jne	SHORT $LN2@pypy_g_ll_@159
$LN1@pypy_g_ll_@159:
	call	_pypy_debug_catch_fatal_exception
$LN2@pypy_g_ll_@159:

; 58408: 	(&pypy_g_ExcData)->ed_exc_value = ((struct pypy_object0 *) NULL);

	xor	eax, eax

; 58409: 	(&pypy_g_ExcData)->ed_exc_type = ((struct pypy_object_vtable0 *) NULL);
; 58410: 	l_v21687 = (struct pypy_exceptions_Exception0 *)l_v21682;
; 58411: 	l_v21688 = (void*)l_exp_p_0;
; 58412: 	OP_TRACK_ALLOC_STOP(l_v21688, /* nothing */);

	push	esi
	mov	DWORD PTR _pypy_g_ExcData+4, eax
	mov	DWORD PTR _pypy_g_ExcData, eax
	call	_pypy_debug_alloc_stop
    ;; expected {4(%ebp) | 12(%esp), 8(%esp), 4(%esp), (%ebp) | }

; 58413: 	OP_RAW_FREE(l_v21688, /* nothing */);

	push	esi
	call	_PyObject_Free
    ;; expected {4(%ebp) | 16(%esp), 12(%esp), 8(%esp), (%ebp) | }

; 58414: 	l_v21691 = (struct pypy_object0 *)l_v21687;
; 58415: 	pypy_g_RPyReRaiseException(l_v21683, l_v21691);

	push	ebx
	push	edi
	call	_pypy_g_RPyReRaiseException
	add	esp, 16					; 00000010H

; 58416: 	pypy_asm_gc_nocollect(pypy_g_RPyReRaiseException);
; 58417: 	l_v21695 = ((struct pypy_tuple2_0 *) NULL);

	xor	eax, eax

; 58423: 	goto block8;
; 58424: }

	pop	edi
	pop	esi
	pop	ebx
	mov	esp, ebp
	pop	ebp
	ret	0
$block16$88328:

; 58390: 		goto block17;
; 58391: 	}
; 58392: 	goto block16;
; 58393: 
; 58394:     block16:
; 58395: 	l_v21677 = RPyBareItem(l_exp_p_0, 0L);
; 58396: 	l_v21678 = (long)(l_v21677);

	mov	edi, DWORD PTR [esi]

; 58397: 	l_v21679 = (void*)l_exp_p_0;
; 58398: 	OP_TRACK_ALLOC_STOP(l_v21679, /* nothing */);

	push	esi
	call	_pypy_debug_alloc_stop
    ;; expected {4(%ebp) | 12(%esp), 8(%esp), 4(%esp), (%ebp) | }

; 58399: 	OP_RAW_FREE(l_v21679, /* nothing */);

	push	esi
	call	_PyObject_Free
    ;; expected {4(%ebp) | 16(%esp), 12(%esp), 8(%esp), (%ebp) | }

; 58400: 	l_v21637 = l_v21678;
; 58401: 	l_v21638 = l_mantissa_0;

	fld	QWORD PTR _l_mantissa_0$[esp+72]
	add	esp, 8

; 58402: 	goto block3;

	jmp	$LN30@pypy_g_ll_@159
$LN5@pypy_g_ll_@159:

; 58365: 		goto block13;
; 58366: 	}
; 58367: 	l_v21639 = l_v21668;

	mov	esi, eax
$block4$88260:
$block5$88263:

; 58301: 		goto block12;
; 58302: 	}
; 58303: 	l_v21639 = l_v21648;
; 58304: 	goto block4;
; 58305: 
; 58306:     block4:
; 58307: 	OP_INT_IS_TRUE(RUNNING_ON_LLINTERP, l_v21653);
; 58308: 	if (l_v21653) {
; 58309: 		goto block10;
; 58310: 	}
; 58311: 	goto block5;
; 58312: 
; 58313:     block5:
; 58314: 	l_v21654 = (struct pypy_header0 *)l_v21639;
; 58315: 	RPyField(l_v21654, h_tid) = (GROUP_MEMBER_OFFSET(struct group_pypy_g_typeinfo_s, member20)+0L);

	test	esi, esi
	jne	SHORT $LN18@pypy_g_ll_@159
	call	_RPyAbort
$LN18@pypy_g_ll_@159:

; 58316: 	OP_ADR_ADD(l_v21639, (0 + ROUND_UP_FOR_ALLOCATION(sizeof(struct pypy_tuple2_0), sizeof(struct pypy_forwarding_stub0))), l_v21656);
; 58317: 	(&pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC)->ssgc_inst_free = l_v21656;
; 58318: 	OP_ADR_ADD(l_v21639, 0, l_v21658);
; 58319: 	l_v21659 = (void*)l_v21658;
; 58320: 	l_v21696 = l_v21659;
; 58321: 	goto block6;
; 58322: 
; 58323:     block6:
; 58324: 	l_v21640 = (struct pypy_tuple2_0 *)l_v21696;
; 58325: 	l_v21660 = (l_v21640 != NULL);
; 58326: 	if (!l_v21660) {
; 58327: 		goto block9;
; 58328: 	}
; 58329: 	goto block7;
; 58330: 
; 58331:     block7:
; 58332: 	RPyField(l_v21640, t_item0) = l_v21638;

	fld	QWORD PTR _l_v21638$[esp+64]
	mov	DWORD PTR [esi], 81			; 00000051H
	lea	ecx, DWORD PTR [esi+24]
	mov	DWORD PTR _pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+4, ecx
	fstp	QWORD PTR [esi+8]

; 58333: 	RPyField(l_v21640, t_item1) = l_v21637;

	mov	DWORD PTR [esi+16], edi

; 58423: 	goto block8;
; 58424: }

	pop	edi
	mov	eax, esi
	pop	esi
$block6$88281:
$block8$88289:
	pop	ebx
	mov	esp, ebp
	pop	ebp
	ret	0
_pypy_g_ll_math_ll_math_frexp ENDP
_TEXT	ENDS
