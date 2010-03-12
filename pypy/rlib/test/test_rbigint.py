from __future__ import division
import py
import operator, sys
from random import random, randint, sample
from pypy.rlib.rbigint import rbigint, SHIFT, MASK, KARATSUBA_CUTOFF
from pypy.rlib import rbigint as lobj
from pypy.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong, intmask
from pypy.rpython.test.test_llinterp import interpret

class TestRLong(object):
    def test_simple(self):
        for op1 in [-2, -1, 0, 1, 2, 50]:
            for op2 in [-2, -1, 0, 1, 2, 50]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                for op in "add sub mul".split():
                    r1 = getattr(rl_op1, op)(rl_op2)
                    r2 = getattr(operator, op)(op1, op2)
                    assert r1.tolong() == r2
            
    def test_floordiv(self):
        for op1 in [-12, -2, -1, 1, 2, 50]:
            for op2 in [-4, -2, -1, 1, 2, 8]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                r1 = rl_op1.floordiv(rl_op2)
                r2 = op1 // op2
                assert r1.tolong() == r2

    def test_truediv(self):
        for op1 in [-12, -2, -1, 1, 2, 50]:
            for op2 in [-4, -2, -1, 1, 2, 8]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                r1 = rl_op1.truediv(rl_op2)
                r2 = op1 / op2
                assert r1 == r2

    def test_mod(self):
        for op1 in [-50, -12, -2, -1, 1, 2, 50, 52]:
            for op2 in [-4, -2, -1, 1, 2, 8]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                r1 = rl_op1.mod(rl_op2)
                r2 = op1 % op2
                assert r1.tolong() == r2

    def test_pow(self):
        for op1 in [-50, -12, -2, -1, 1, 2, 50, 52]:
            for op2 in [0, 1, 2, 8, 9, 10, 11]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                r1 = rl_op1.pow(rl_op2)
                r2 = op1 ** op2
                assert r1.tolong() == r2

    def test_touint(self):
        import sys
        from pypy.rlib.rarithmetic import r_uint
        result = r_uint(sys.maxint + 42)
        rl = rbigint.fromint(sys.maxint).add(rbigint.fromint(42))
        assert rl.touint() == result

def gen_signs(l):
    for s in l:
        if s == 0:
            yield s
        else:
            yield s
            yield -s


class Test_rbigint(object):

    def test_args_from_long(self):
        BASE = 1 << SHIFT
        assert rbigint.fromlong(0).eq(rbigint([0], 0))
        assert rbigint.fromlong(17).eq(rbigint([17], 1))
        assert rbigint.fromlong(BASE-1).eq(rbigint([intmask(BASE-1)], 1))
        assert rbigint.fromlong(BASE).eq(rbigint([0, 1], 1))
        assert rbigint.fromlong(BASE**2).eq(rbigint([0, 0, 1], 1))
        assert rbigint.fromlong(-17).eq(rbigint([17], -1))
        assert rbigint.fromlong(-(BASE-1)).eq(rbigint([intmask(BASE-1)], -1))
        assert rbigint.fromlong(-BASE).eq(rbigint([0, 1], -1))
        assert rbigint.fromlong(-(BASE**2)).eq(rbigint([0, 0, 1], -1))
#        assert rbigint.fromlong(-sys.maxint-1).eq(
#            rbigint.digits_for_most_neg_long(-sys.maxint-1), -1)

    def test_args_from_int(self):
        BASE = 1 << SHIFT
        assert rbigint.fromrarith_int(0).eq(rbigint([0], 0))
        assert rbigint.fromrarith_int(17).eq(rbigint([17], 1))
        assert rbigint.fromrarith_int(BASE-1).eq(rbigint([intmask(BASE-1)], 1))
        assert rbigint.fromrarith_int(BASE).eq(rbigint([0, 1], 1))
        assert rbigint.fromrarith_int(BASE**2).eq(rbigint([0, 0, 1], 1))
        assert rbigint.fromrarith_int(-17).eq(rbigint([17], -1))
        assert rbigint.fromrarith_int(-(BASE-1)).eq(rbigint([intmask(BASE-1)], -1))
        assert rbigint.fromrarith_int(-BASE).eq(rbigint([0, 1], -1))
        assert rbigint.fromrarith_int(-(BASE**2)).eq(rbigint([0, 0, 1], -1))
#        assert rbigint.fromrarith_int(-sys.maxint-1).eq((
#            rbigint.digits_for_most_neg_long(-sys.maxint-1), -1)

    def test_args_from_uint(self):
        BASE = 1 << SHIFT
        assert rbigint.fromrarith_int(r_uint(0)).eq(rbigint([0], 0))
        assert rbigint.fromrarith_int(r_uint(17)).eq(rbigint([17], 1))
        assert rbigint.fromrarith_int(r_uint(BASE-1)).eq(rbigint([intmask(BASE-1)], 1))
        assert rbigint.fromrarith_int(r_uint(BASE)).eq(rbigint([0, 1], 1))
        assert rbigint.fromrarith_int(r_uint(BASE**2)).eq(rbigint([0], 0))
        assert rbigint.fromrarith_int(r_uint(sys.maxint)).eq(
            rbigint.fromint(sys.maxint))
        assert rbigint.fromrarith_int(r_uint(sys.maxint+1)).eq(
            rbigint.fromlong(sys.maxint+1))
        assert rbigint.fromrarith_int(r_uint(2*sys.maxint+1)).eq(
            rbigint.fromlong(2*sys.maxint+1))

    def test_add(self):
        x = 123456789123456789000000L
        y = 123858582373821923936744221L
        for i in [-1, 1]:
            for j in [-1, 1]:
                f1 = rbigint.fromlong(x * i)
                f2 = rbigint.fromlong(y * j)
                result = f1.add(f2)
                assert result.tolong() == x * i + y * j

    def test_sub(self):
        x = 12378959520302182384345L
        y = 88961284756491823819191823L
        for i in [-1, 1]:
            for j in [-1, 1]:
                f1 = rbigint.fromlong(x * i)
                f2 = rbigint.fromlong(y * j)
                result = f1.sub(f2)
                assert result.tolong() == x * i - y * j

    def test_subzz(self):
        w_l0 = rbigint.fromint(0)
        assert w_l0.sub(w_l0).tolong() == 0

    def test_mul(self):
        x = -1238585838347L
        y = 585839391919233L
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        result = f1.mul(f2)
        assert result.tolong() == x * y
        # also test a * a, it has special code
        result = f1.mul(f1)
        assert result.tolong() == x * x

    def test_tofloat(self):
        x = 12345678901234567890L ** 10
        f1 = rbigint.fromlong(x)
        d = f1.tofloat()
        assert d == float(x)
        x = x ** 100
        f1 = rbigint.fromlong(x)
        assert raises(OverflowError, f1.tofloat)
        f2 = rbigint([0, 2097152], 1)
        d = f2.tofloat()
        assert d == float(2097152 << SHIFT)

    def test_fromfloat(self):
        x = 1234567890.1234567890
        f1 = rbigint.fromfloat(x)
        y = f1.tofloat()
        assert f1.tolong() == long(x)
        # check overflow
        #x = 12345.6789e10000000000000000000000000000
        # XXX don't use such consts. marshal doesn't handle them right.
        x = 12345.6789e200
        x *= x
        assert raises(OverflowError, rbigint.fromfloat, x)

    def test_eq(self):
        x = 5858393919192332223L
        y = 585839391919233111223311112332L
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(-x)
        f3 = rbigint.fromlong(y)
        assert f1.eq(f1)
        assert f2.eq(f2)
        assert f3.eq(f3)
        assert not f1.eq(f2)
        assert not f1.eq(f3)

    def test_lt(self):
        val = [0, 0x111111111111, 0x111111111112, 0x111111111112FFFF]
        for x in gen_signs(val):
            for y in gen_signs(val):
                f1 = rbigint.fromlong(x)
                f2 = rbigint.fromlong(y)
                assert (x < y) ==  f1.lt(f2)

    def test_int_conversion(self):
        f1 = rbigint.fromlong(12332)
        f2 = rbigint.fromint(12332)
        assert f2.tolong() == f1.tolong()
        assert f2.toint()
        assert rbigint.fromlong(42).tolong() == 42
        assert rbigint.fromlong(-42).tolong() == -42

        u = f2.touint()
        assert u == 12332
        assert type(u) is r_uint

    def test_conversions(self):
        for v in (0, 1, -1, sys.maxint, -sys.maxint-1):
            assert rbigint.fromlong(long(v)).tolong() == long(v)
            l = rbigint.fromint(v)
            assert l.toint() == v
            if v >= 0:
                u = l.touint()
                assert u == v
                assert type(u) is r_uint
            else:
                py.test.raises(ValueError, l.touint)

        toobig_lv1 = rbigint.fromlong(sys.maxint+1)
        assert toobig_lv1.tolong() == sys.maxint+1
        toobig_lv2 = rbigint.fromlong(sys.maxint+2)
        assert toobig_lv2.tolong() == sys.maxint+2
        toobig_lv3 = rbigint.fromlong(-sys.maxint-2)
        assert toobig_lv3.tolong() == -sys.maxint-2

        for lv in (toobig_lv1, toobig_lv2, toobig_lv3):
            py.test.raises(OverflowError, lv.toint)

        lmaxuint = rbigint.fromlong(2*sys.maxint+1)
        toobig_lv4 = rbigint.fromlong(2*sys.maxint+2)

        u = lmaxuint.touint()
        assert u == 2*sys.maxint+1

        py.test.raises(ValueError, toobig_lv3.touint)
        py.test.raises(OverflowError, toobig_lv4.touint)


    def test_pow_lll(self):
        x = 10L
        y = 2L
        z = 13L
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        f3 = rbigint.fromlong(z)
        v = f1.pow(f2, f3)
        assert v.tolong() == pow(x, y, z)
        f1, f2, f3 = [rbigint.fromlong(i)
                      for i in (10L, -1L, 42L)]
        py.test.raises(TypeError, f1.pow, f2, f3)
        f1, f2, f3 = [rbigint.fromlong(i)
                      for i in (10L, 5L, 0L)]
        py.test.raises(ValueError, f1.pow, f2, f3)

    def test_pow_lln(self):
        x = 10L
        y = 2L
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        v = f1.pow(f2)
        assert v.tolong() == x ** y

    def test_normalize(self):
        f1 = rbigint([1, 0], 1)
        f1._normalize()
        assert len(f1.digits) == 1
        f0 = rbigint([0], 0)
        assert f1.sub(f1).eq(f0)

    def test_invert(self):
        x = 3 ** 40
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(-x)
        r1 = f1.invert()
        r2 = f2.invert()
        assert r1.tolong() == -(x + 1)
        assert r2.tolong() == -(-x + 1)

    def test_shift(self):
        negative = -23
        for x in gen_signs([3L ** 30L, 5L ** 20L, 7 ** 300, 0L, 1L]):
            f1 = rbigint.fromlong(x)
            py.test.raises(ValueError, f1.lshift, negative)
            py.test.raises(ValueError, f1.rshift, negative)
            for y in [0L, 1L, 32L, 2304L, 11233L, 3 ** 9]:
                res1 = f1.lshift(int(y)).tolong()
                res2 = f1.rshift(int(y)).tolong()
                assert res1 == x << y
                assert res2 == x >> y

    def test_bitwise(self):
        for x in gen_signs([0, 1, 5, 11, 42, 43, 3 ** 30]):
            for y in gen_signs([0, 1, 5, 11, 42, 43, 3 ** 30, 3 ** 31]):
                lx = rbigint.fromlong(x)
                ly = rbigint.fromlong(y)
                for mod in "xor and_ or_".split():
                    res1 = getattr(lx, mod)(ly).tolong()
                    res2 = getattr(operator, mod)(x, y)
                    assert res1 == res2

    def test_tostring(self):
        z = rbigint.fromlong(0)
        assert z.str() == '0'
        assert z.repr() == '0L'
        assert z.hex() == '0x0L'
        assert z.oct() == '0L'
        x = rbigint.fromlong(-18471379832321)
        assert x.str() == '-18471379832321'
        assert x.repr() == '-18471379832321L'
        assert x.hex() == '-0x10ccb4088e01L'
        assert x.oct() == '-0414626402107001L'
        assert x.format('.!') == (
            '-!....!!..!!..!.!!.!......!...!...!!!........!')
        assert x.format('abcdefghijkl', '<<', '>>') == '-<<cakdkgdijffjf>>'

    def test_bug_1(self):
        a = rbigint.fromlong(-260566012002303321722013103575165611802035413114370523571517985970903119146285215291155533416475427807866974423149439841327725756828005658754191295994809087809320280074294681950026758288312811442356042692340807896417550222700067702753579399761784070474131037635149818948168511691070322953335739176272622910365829586902906224907432253591195717349172746433645917252849956470742043097671857488808687984974936937393198531638816746133375496901061105863168552515536868445659801937921320743439816979399954242291177429500378469191475860257584018420786462583814660948295622420456034201723416326423603335962947265565263130943743607845486466656418476418168470250055928378188550753407412799673743058221743671551255616401922924945339716159856273901552124064212280377021704945248469685731959689385127980398007781532220934759272116712735714960453264108373398671551492381335420245663126153660439132147185782037977502460780371596093655257982404062421193485596889355995886829663760398816634042131190521665958820147480841884648364911172419526690252752123997784474398064390304387861348712272377394239798859940158400355446891875253301687364211377544588264334532480752608170448214614824592743195324811005568687376657357775314753082365101450518250246694522659852514124844993887610246455390654886001947723458056036434568491624885628458493463036457076876557994173530887569689636475150085157584896384317149712863001575924410465356365220744359819651023350511856985665413799837139110207713222637419493822305417294231235755804223570090901279843944562993668494067416472862544255191694922740021466785813415839038537636203252434616410465425882750379236899419433481221219910352699544289818155750465496884035520473224175838968242973751544180489601650413296015651616296834725022936721050374837209645923011799078406180765136254224653160432350485532916558236511187886040205728660413810261023410048197904230010446088642876209717987090887740019976421912592014066600375956412103968560631965074024041620753826920381707525361879673445199503678061708391707896640363885748625247991660850390946150221513913729996091173773133131890225189064630986207916656744202551412451503273356101322462935617885275965853144343444704926691669657273293204666703512898072198258683719706285195069835543493502675161032489116187622069692993654200740685652627157360996959130403453347654083224412248043390793368967143340589648611252149478198894261334863884457393059141958486145451183004263823354652969965183462963726448733474469749514798522906424890883724926780202541044258203022886876020595422485151804950409950166755366874555828434740032171004838233809398853178488772731722647248612394324321149390505386951062179235246676031381046783794175796805080047738725286430898862883355470814692593559655069839453890111470642889098994389005946762316395275104458893107707110318839219905324157399932418015510323560907704798236836452155437817898814729188459245265619792043305147965178962411969228220664984934132957809193796871874171530228091837207719711362636305927916484527244928543234389063858371939012739858432000000)

        b = rbigint.fromlong(4)

        c = rbigint.fromlong(-106338239662793259730840081832295065771498816856940833696008165438815584980417686604608895346971884917769394031927561256725298929772711322879321393361696892049088965909181189736595867761347336019083746883127398251219384697894361161880597010006115562788942887618399114955271064878243102711874111058553462221395610761115873783457057812896391268438235444365991417075573732724100004047346784535037202050299531029591233086252349804548018155384835618742066822895556578137983546805076058353099547216512597408658946637718054915179937028899202964603576928551959262426346921004319846578906414772153517775387280861867487721363107740289707055950184419061249517558075330964421972823597291877332113158897302951144315480978860428747061439209765294730056119323718330270866241907812176527650320215232153341169940994430206379664550756722308581528186445619877248999398977789445715595671183883983268410651963136012836142558863971524201994294408478883247731406955241176141981742990603952556991912216949229945213071071983247958605165780107344396217423285452800)

        assert a.mul(b).mul(c).tolong() == 110832524129116782583364562456977640731335756529609088759378295006704772245974743173511644458675057302079987629835792236278312771678692303989361636542809838735194579106811404379614655739026463972679329139434164586374108475206967844097441160213284504934202480180032139888482444764983319216438433537832078516985619574162213721865744106517175234637261790280236913670178022378625016733361416185038455904438888246857878950470952325614982157170485741313910674393245003830392267085210311799551545972523346707387178520024611549981852670315070547440401122501891931825875960462166390275427684496325053195440865642204367994829293604398903046728164723158551453976182016937198123809176742966562888182432196414166400096652509342321321743476843344058627686730464867211258480704776704498446616101796263760178703227236505673451858701727913112759267764109714995818122458479126636108139321203958668185214950588580207103541950431274794566843359440350943752742082562538769212434294327810435270399438986112495616227923737414728798069933714673871391498110177949207547505033136836458634606312538096687797027733387424125878584385636111818223911900033354524034387542607682136576871579302279784953384936126882542253555140527486205141616943792484401155746547215597129490560806172364270767368990056371932228780665959134392102455377841234028978996308058186505194783650130179928673727012488256080004895653886144332872432289180496212904959975676585180012865990856545788985871243661381800148419972031058947277513438199225648529875646111686166176519979855679554344140264010483415463326100676133077809735840466471022613923792057235108707948400407624287331530986889046800817902279069703559833421581331256230884071179598459785625245650782029029322150238995195521227505990817653610469722901339231958298390284876126014159379033287075519462149243271172963871032844781784225603388136263417588981496551374805239987026987313762069576871742865088508552110890580500720033327845072452424251933683127950277588406114514844979948727526706389888421544523362606742419244747509102087639447513471188108241157864242701335645555026346619245699752666285865081977746566880559621759751595020851093674855777825451087504404795410611432959365368919126606768430328681016998624963878159228600896476855567188634084921197529066160362616693921167843075792824209694269220559843282666693049363809669507785196417549088417499875428569887061842530632366731211920496861835081751081842566818397316345926010655462157108750820970335096339414909824916313255708868878066428162448128721439720699956849305447074147346861983811454157772370142260519018784555066718855368418469670174688776370877035479525356163764475258378975158984871528660286361965641503971983346012081939513003180866443286265869046461908753885889743448744320141501611168369982279186025200319384649405474996576807017922093590932514280363660550227287802611494334334607843323216686446826866447311048152176684331349978510675393988261003953873381091617333523977851570885851719036027366439199079878330408900672719175802907289051303375145535553930031626633762994181239987601184562172550477892685669393404111413175213787178098834254167127624253002981496188936840854096027552855011170366261745499495417813144239077455025835453607885002118545216683747855456386109509751819274073863878470281232518189103557806573352768345515244126718703747172619569007522184689496709008855313559867161158579502656536285666843995155026521610393549572974321882301537225738400691179905702280583119045478250270608753115619081672106397626905258492908537976623550592167132205686242236595251736145299604679380289665497374792748814099937488988552367986787677665998385383608256021488822227572444336678008598743792369799266926833042608329505013007907469005128713651150644761489785642344749398016890987457554939180946052125679983599966774606430591989594901778520067217343641063899668851213095805105740570942673366384498478828587645324595977304487968297570444369020807943787596717818846249373957402470969494527872843184588264064266126564410921857079085523025929016927582700388097395606532665822492862195671710755988072038400000000


class TestInternalFunctions(object):
    def test__inplace_divrem1(self):
        # signs are not handled in the helpers!
        for x, y in [(1238585838347L, 3), (1234123412311231L, 1231231), (99, 100)]:
            f1 = rbigint.fromlong(x)
            f2 = y
            remainder = lobj._inplace_divrem1(f1, f1, f2)
            assert (f1.tolong(), remainder) == divmod(x, y)
        out = rbigint([99, 99], 1)
        remainder = lobj._inplace_divrem1(out, out, 100)

    def test__divrem1(self):
        # signs are not handled in the helpers!
        x = 1238585838347L
        y = 3
        f1 = rbigint.fromlong(x)
        f2 = y
        div, rem = lobj._divrem1(f1, f2)
        assert (div.tolong(), rem) == divmod(x, y)

    def test__muladd1(self):
        x = 1238585838347L
        y = 3
        z = 42
        f1 = rbigint.fromlong(x)
        f2 = y
        f3 = z
        prod = lobj._muladd1(f1, f2, f3)
        assert prod.tolong() == x * y + z

    def test__x_divrem(self):
        x = 12345678901234567890L
        for i in range(100):
            y = long(randint(0, 1 << 30))
            y <<= 30
            y += randint(0, 1 << 30)
            f1 = rbigint.fromlong(x)
            f2 = rbigint.fromlong(y)
            div, rem = lobj._x_divrem(f1, f2)
            assert div.tolong(), rem.tolong() == divmod(x, y)

    def test__divrem(self):
        x = 12345678901234567890L
        for i in range(100):
            y = long(randint(0, 1 << 30))
            y <<= 30
            y += randint(0, 1 << 30)
            for sx, sy in (1, 1), (1, -1), (-1, -1), (-1, 1):
                sx *= x
                sy *= y
                f1 = rbigint.fromlong(sx)
                f2 = rbigint.fromlong(sy)
                div, rem = lobj._x_divrem(f1, f2)
                assert div.tolong(), rem.tolong() == divmod(sx, sy)

    # testing Karatsuba stuff
    def test__v_iadd(self):
        f1 = rbigint([lobj.MASK] * 10, 1)
        f2 = rbigint([1], 1)
        carry = lobj._v_iadd(f1, 1, len(f1.digits)-1, f2, 1)
        assert carry == 1
        assert f1.tolong() == lobj.MASK

    def test__v_isub(self):
        f1 = rbigint([lobj.MASK] + [0] * 9 + [1], 1)
        f2 = rbigint([1], 1)
        borrow = lobj._v_isub(f1, 1, len(f1.digits)-1, f2, 1)
        assert borrow == 0
        assert f1.tolong() == (1 << lobj.SHIFT) ** 10 - 1

    def test__kmul_split(self):
        split = 5
        diglo = [0] * split
        dighi = [lobj.MASK] * split
        f1 = rbigint(diglo + dighi, 1)
        hi, lo = lobj._kmul_split(f1, split)
        assert lo.digits == [0]
        assert hi.digits == dighi

    def test__k_mul(self):
        digs = KARATSUBA_CUTOFF * 5
        f1 = rbigint([lobj.MASK] * digs, 1)
        f2 = lobj._x_add(f1,rbigint([1], 1))
        ret = lobj._k_mul(f1, f2)
        assert ret.tolong() == f1.tolong() * f2.tolong()

    def test__k_lopsided_mul(self):
        digs_a = KARATSUBA_CUTOFF + 3
        digs_b = 3 * digs_a
        f1 = rbigint([lobj.MASK] * digs_a, 1)
        f2 = rbigint([lobj.MASK] * digs_b, 1)
        ret = lobj._k_lopsided_mul(f1, f2)
        assert ret.tolong() == f1.tolong() * f2.tolong()

    def test_longlong(self):
        max = 1L << (r_longlong.BITS-1)
        f1 = rbigint.fromlong(max-1)    # fits in r_longlong
        f2 = rbigint.fromlong(-max)     # fits in r_longlong
        f3 = rbigint.fromlong(max)      # overflows
        f4 = rbigint.fromlong(-max-1)   # overflows
        assert f1.tolonglong() == max-1
        assert f2.tolonglong() == -max
        py.test.raises(OverflowError, f3.tolonglong)
        py.test.raises(OverflowError, f4.tolonglong)

    def test_uintmask(self):
        assert rbigint.fromint(-1).uintmask() == r_uint(-1)
        assert rbigint.fromint(0).uintmask() == r_uint(0)
        assert (rbigint.fromint(sys.maxint).uintmask() ==
                r_uint(sys.maxint))
        assert (rbigint.fromlong(sys.maxint+1).uintmask() ==
                r_uint(-sys.maxint-1))

    def test_ulonglongmask(self):
        assert rbigint.fromlong(-1).ulonglongmask() == r_ulonglong(-1)
        assert rbigint.fromlong(0).ulonglongmask() == r_ulonglong(0)
        assert (rbigint.fromlong(sys.maxint).ulonglongmask() ==
                r_ulonglong(sys.maxint))
        assert (rbigint.fromlong(9**50).ulonglongmask() ==
                r_ulonglong(9**50))
        assert (rbigint.fromlong(-9**50).ulonglongmask() ==
                r_ulonglong(-9**50))

BASE = 2 ** SHIFT

class TestTranslatable(object):
    def test_square(self):
        def test():
            x = rbigint([1410065408, 4], 1)
            y = x.mul(x)
            return y.str()
        res = interpret(test, [])
        assert "".join(res.chars) == test()

    def test_add(self):
        x = rbigint.fromint(-2147483647)
        y = rbigint.fromint(-1)
        z = rbigint.fromint(-2147483648)
        def test():
            return x.add(y).eq(z)
        assert test()
        res = interpret(test, [])
        assert res

    def test_args_from_rarith_int(self):
        from pypy.rpython.tool.rfficache import platform
        classlist = platform.numbertype_to_rclass.values()
        fnlist = []
        for r in classlist:
            if r is int:
                mask = sys.maxint*2+1
                signed = True
            else:
                mask = r.MASK
                signed = r.SIGNED
            values = [0, -1, mask>>1, -(mask>>1)-1]
            if not signed:
                values = [x & mask for x in values]
            values = [r(x) for x in values]

            def fn(i):
                n = rbigint.fromrarith_int(values[i])
                return n.str()

            for i in range(len(values)):
                res = fn(i)
                assert res == str(long(values[i]))
                res = interpret(fn, [i])
                assert ''.join(res.chars) == str(long(values[i]))
