from rope import rope_svg
import math
F = {}
def svg(name, h, label, body, w=340):
    F[name] = (f'<svg class="dg" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>', label)

def sun(cx, cy, r=11):
    rays = ''.join(f'<line x1="{cx+(r+4)*math.cos(a):.1f}" y1="{cy+(r+4)*math.sin(a):.1f}" x2="{cx+(r+10)*math.cos(a):.1f}" y2="{cy+(r+10)*math.sin(a):.1f}" class="h"/>' for a in [i*math.pi/4 for i in range(8)])
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" class="h hfl"/>{rays}'
def flame(cx, base, s=1.0, cls='h hfl'):
    return (f'<path d="M{cx-14*s:.1f} {base} C{cx-18*s:.1f} {base-18*s:.1f} {cx-6*s:.1f} {base-22*s:.1f} {cx-4*s:.1f} {base-34*s:.1f} '
            f'C{cx+4*s:.1f} {base-26*s:.1f} {cx+6*s:.1f} {base-40*s:.1f} {cx+10*s:.1f} {base-46*s:.1f} C{cx+14*s:.1f} {base-30*s:.1f} {cx+20*s:.1f} {base-20*s:.1f} {cx+14*s:.1f} {base} Z" class="{cls}"/>')
def lbl(x, y, t, cls='', anchor='start'):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{t}</text>'
def lead(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="m t1"/>'
def arrow(x1, y1, x2, y2, cls='k', m='aK'):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}" marker-end="url(#{m})"/>'

# ---------------- WATER ----------------
svg('water-bend', 170, 'Dry stream bed seen from above, with dig spots on the outside of each bend', f'''
<path d="M5 58 C88 58 105 132 163 126 S258 42 335 66" class="bed"/>
<path d="M10 40 C90 40 110 115 165 108 S255 25 330 48" class="m"/>
<path d="M10 76 C80 76 100 150 160 144 S260 60 330 84" class="m"/>
<path d="M30 58 C88 58 105 132 163 126 S258 42 315 64" class="a d" marker-end="url(#aA)"/>
<path d="M140 136 l14 14 m0 -14 l-14 14" class="h t3"/>
<path d="M247 37 l14 14 m0 -14 l-14 14" class="h t3"/>
{lbl(170,163,'Dig on the outside of bends','tb','middle')}
{lbl(240,22,'Dig here too','tb','end')}''')

leaves = ''.join(f'<ellipse cx="{x}" cy="{y}" rx="13" ry="5" transform="rotate({r} {x} {y})" class="g gf"/>'
                 for x, y, r in [(82,64,-35),(96,84,30),(118,72,-30),(132,96,35),(152,84,-25),(168,108,40),(186,98,-20),(200,122,35),(218,112,-15),(226,132,45)])
svg('water-bag', 190, 'Clear plastic bag tied over a leafy branch in sun, with water collecting in the low corner', f'''
<line x1="30" y1="10" x2="30" y2="190" class="w t5"/>
<path d="M30 80 C90 72 160 92 236 128" class="w t3"/>
{leaves}
<path d="M66 70 C120 30 250 52 268 120 C276 160 246 178 226 172 C190 164 120 120 70 88 Z" class="m bag"/>
<rect x="63" y="70" width="9" height="20" rx="2" class="k kf"/>
<ellipse cx="250" cy="164" rx="17" ry="7" transform="rotate(-28 250 164)" class="afs"/>
<circle cx="204" cy="78" r="2.5" class="afs"/><circle cx="236" cy="96" r="2.5" class="afs"/><circle cx="256" cy="124" r="2.5" class="afs"/>
{sun(306,32)}
{lbl(96,24,'Clear bag, tied tight','tb')}{lead(120,28,128,46)}
{lbl(40,152,'Leafy, non-poisonous','')}{lbl(40,166,'branch in full sun','')}
{lbl(336,186,'Water collects in the low corner','tb','end')}''')

svg('water-safe', 175, 'Boil water for 1 minute, or 3 minutes above 6,500 feet; or add 8 drops of 6 percent bleach per gallon and wait 30 minutes', f'''
{lbl(80,22,'Boil','tb','middle')}
<path d="M30 80 H130 V140 Q130 150 120 150 H40 Q30 150 30 140 Z" class="k"/>
<path d="M30 90 H18 M130 90 H142" class="k t3"/>
<path d="M34 98 H126" class="a"/>
<circle cx="55" cy="115" r="4" class="a t1"/><circle cx="80" cy="108" r="3" class="a t1"/><circle cx="102" cy="121" r="5" class="a t1"/><circle cx="68" cy="133" r="3" class="a t1"/><circle cx="112" cy="138" r="3" class="a t1"/>
<path d="M60 76 q-5 -6 0 -11 M100 76 q-5 -6 0 -11" class="m t1"/>
{flame(55,170,0.42)}{flame(80,170,0.5)}{flame(105,170,0.42)}
{lbl(80,46,'1 minute rolling boil','','middle')}{lbl(80,62,'3 min above 6,500 ft','tm','middle')}
<line x1="170" y1="20" x2="170" y2="160" class="m t1 d"/>
{lbl(260,22,'No fire? Bleach','tb','middle')}
<rect x="196" y="76" width="40" height="66" rx="6" class="k"/><rect x="207" y="62" width="18" height="14" class="k"/><rect x="204" y="54" width="24" height="8" rx="2" class="k kf"/>
{lbl(216,114,'6%','tb','middle')}
<path d="M254 82 q6 9 0 14 q-6 -5 0 -14z M254 102 q6 9 0 14 q-6 -5 0 -14z M254 122 q6 9 0 14 q-6 -5 0 -14z" class="afs"/>
<path d="M276 92 h44 a6 6 0 0 1 6 6 v44 a6 6 0 0 1 -6 6 h-44 a6 6 0 0 1 -6 -6 v-44 a6 6 0 0 1 6 -6z" class="k"/>
<path d="M286 92 v-12 h20 v12" class="k"/><path d="M272 116 H324" class="a"/>
{lbl(298,138,'1 gal','tm','middle')}
{lbl(260,40,'8 drops of 6% per gallon','','middle')}
{lbl(260,168,'Stir, wait 30 minutes','tb','middle')}''')

# ---------------- SHELTER ----------------
svg('shelter-site', 200, 'Valley cross-section: wind on ridgetops, cold air and floods in the valley floor, a level bench as the best site', f'''
<path d="M0 55 L45 28 L85 62 L125 112 L155 150 L190 154 L218 130 L236 112 L264 110 L282 84 L305 48 L340 58 L340 200 L0 200 Z" class="gr m"/>
<path d="M118 104 Q170 96 228 121 L218 130 L190 154 L155 150 Z" class="af"/>
{arrow(78,66,112,98,'a d','aA')}{arrow(298,58,272,90,'a d','aA')}
{arrow(8,10,58,10,'m','aM')}{arrow(16,19,66,19,'m','aM')}
{lbl(74,16,'Ridgetops: wind','')}
<path d="M240 110 L250 92 L260 110 Z" class="k gf"/>
{lbl(232,70,'Good: level bench,','tb','end')}{lbl(232,84,'sheltered, above','','end')}{lbl(232,98,'flood level','','end')}{lead(235,86,247,98)}
{lbl(170,176,'Valley floor: cold air pools,','','middle')}{lbl(170,190,'floods run here','','middle')}''')

ribs = ''.join(f'<line x1="{x}" y1="{88+(x-55)*77/255:.1f}" x2="{x-16}" y2="165" class="w t1"/>' for x in range(100, 300, 28))
svg('shelter-debris', 195, 'Debris hut: ridgepole propped at hip height, ribs, debris an arm’s length thick, thick leaf bed inside', f'''
<rect x="0" y="165" width="340" height="30" class="gr"/><line x1="0" y1="165" x2="340" y2="165" class="m"/>
<path d="M78 165 L80 156 Q170 148 272 160 L280 165 Z" class="gf g t1"/>
<line x1="70" y1="165" x2="70" y2="96" class="w t3"/><path d="M70 102 L60 86 M70 102 L80 86" class="w t3"/>
<line x1="52" y1="87" x2="312" y2="166" class="w t5"/>
{ribs}
<path d="M36 165 C28 104 50 60 92 62 C134 64 222 110 334 165" class="w wf t1"/>
<path d="M44 165 A15 15 0 0 1 72 165" class="k"/>
{lbl(150,36,'Ridgepole at hip height','tb')}{lead(170,40,148,112)}
{lbl(214,82,'Debris an arm’s','')}{lbl(214,96,'length thick','')}{lead(212,94,190,104)}
{lbl(330,186,'Thick leaf bed','tb','end')}{lead(270,176,240,158)}
{lbl(10,186,'Door: plug it from inside','')}''')

svg('shelter-leanto', 190, 'Lean-to with boughs on the windward side and a fire with a log reflector wall', f'''
<rect x="0" y="165" width="340" height="25" class="gr"/><line x1="0" y1="165" x2="340" y2="165" class="m"/>
<line x1="122" y1="8" x2="122" y2="165" class="w t5"/>
<path d="M118 64 L128 70 L46 170 L32 165 Z" class="g gf"/>
<path d="M116 76 l-10 -4 M104 92 l-10 -4 M92 108 l-10 -4 M80 124 l-10 -4 M68 140 l-10 -4 M56 156 l-10 -4" class="g t1"/>
<line x1="122" y1="70" x2="40" y2="166" class="w t3"/>
<circle cx="122" cy="70" r="6" class="w wfs"/>
<path d="M58 160 Q90 148 122 156 Q120 165 60 165 Z" class="k gf"/>
<line x1="180" y1="165" x2="214" y2="152" class="w t5"/><line x1="182" y1="152" x2="214" y2="165" class="w t5"/>
{flame(197,158,0.75)}
<line x1="244" y1="110" x2="244" y2="166" class="w t3"/><line x1="262" y1="110" x2="262" y2="166" class="w t3"/>
<circle cx="253" cy="158" r="7" class="w wfs"/><circle cx="253" cy="144" r="7" class="w wfs"/><circle cx="253" cy="130" r="7" class="w wfs"/><circle cx="253" cy="116" r="7" class="w wfs"/>
{arrow(212,128,238,124,'h','aH')}<path d="M238 112 C200 96 160 104 134 128" class="h" marker-end="url(#aH)"/>
{arrow(4,96,30,96,'m','aM')}{lbl(4,88,'Wind','tm')}
{lbl(136,22,'Branches on the','')}{lbl(136,36,'windward side','')}
{lbl(336,40,'Log wall','tb','end')}{lbl(336,54,'reflects heat','','end')}{lbl(336,68,'back in','','end')}{lead(300,72,262,112)}
{lbl(197,184,'Fire','','middle')}''')

svg('shelter-tarp', 180, 'Tarp pitched as an A-frame over a ridgeline, with the low end facing the wind', f'''
<line x1="0" y1="160" x2="340" y2="160" class="m"/>
<line x1="22" y1="6" x2="22" y2="160" class="w t5"/><line x1="318" y1="6" x2="318" y2="160" class="w t5"/>
<line x1="22" y1="40" x2="318" y2="86" class="k t1"/>
<path d="M44 43 L296 82 L284 158 L66 158 Z" class="g gf"/>
<path d="M44 43 L20 158 M44 43 L70 158" class="g d t1"/>
<path d="M66 158 l-6 8 M284 158 l6 8" class="k"/>
{arrow(338,118,306,118,'m','aM')}{arrow(338,134,306,134,'m','aM')}{lbl(334,108,'Wind','tm','end')}
{lbl(110,26,'Ridgeline tied between trees','')}
{lbl(296,40,'Low end','tb','end')}{lbl(296,54,'into the wind','','end')}{lead(286,58,290,80)}
{lbl(110,132,'Open, high end','','start')}''')

svg('shelter-snow', 200, 'Snow trench cross-section: roof with a vent hole, raised sleeping shelf, cold air sinking to a lower trench', f'''
<path d="M0 60 H100 V140 H190 V175 H240 V60 H340 V200 H0 Z" class="snow"/>
<line x1="92" y1="60" x2="166" y2="60" class="w t3"/><line x1="184" y1="60" x2="248" y2="60" class="w t3"/>
<rect x="96" y="44" width="34" height="16" rx="3" class="snow"/><rect x="132" y="44" width="32" height="16" rx="3" class="snow"/>
<rect x="186" y="44" width="30" height="16" rx="3" class="snow"/><rect x="218" y="44" width="30" height="16" rx="3" class="snow"/>
{arrow(175,74,175,18,'m','aM')}{lbl(184,26,'Vent hole','tb')}
<ellipse cx="145" cy="132" rx="38" ry="8" class="k gf"/>
{lbl(8,92,'Sleep on a','tb')}{lbl(8,106,'raised shelf','')}{lead(70,104,110,130)}
{lbl(336,140,'Cold air sinks','tb','end')}{lbl(336,154,'to the low end','','end')}{lead(270,158,228,168)}
{lbl(170,194,'Snow','tm','middle')}''')

svg('shelter-desert', 190, 'Desert shade shelter: two layers with an air gap over a shallow trench', f'''
{sun(34,28)}
<path d="M0 110 H80 L90 150 H190 L200 110 H340 V190 H0 Z" class="gr m"/>
<line x1="80" y1="110" x2="80" y2="58" class="w t3"/><line x1="200" y1="110" x2="200" y2="58" class="w t3"/>
<line x1="68" y1="62" x2="212" y2="62" class="k t3"/><line x1="68" y1="84" x2="212" y2="84" class="g t3"/>
<path d="M50 44 L110 60 M44 54 L150 60" class="h d t1"/>
<ellipse cx="140" cy="142" rx="40" ry="7" class="k"/>
{lbl(226,60,'Top layer: sun','')}
<path d="M220 66 v14" class="m"/>{lbl(226,77,'Air gap','tb')}
{lbl(226,92,'Shade layer','')}
{lbl(170,176,'Dig in: deeper sand is cooler','','middle')}''')

# ---------------- FIRE ----------------
svg('fire-sizes', 130, 'Fire materials: tinder, kindling from pencil-lead to pencil thick, and wrist-thick fuel', f'''
<path d="M30 58 c5 -22 34 -24 42 -6 c8 16 -12 30 -26 22 c-14 -8 -4 -26 12 -22 c12 4 10 16 0 18 M40 48 c8 -6 20 -4 22 6 M36 66 c10 8 26 6 30 -6" class="w t1"/>
{lbl(55,100,'Tinder','tb','middle')}{lbl(55,116,'fine and dry','tm','middle')}
<line x1="124" y1="40" x2="196" y2="46" class="w t1"/><line x1="126" y1="54" x2="198" y2="58" class="w"/><line x1="124" y1="70" x2="196" y2="72" class="w t3"/>
{lbl(160,100,'Kindling','tb','middle')}{lbl(160,116,'up to pencil-thick','tm','middle')}
<line x1="244" y1="44" x2="316" y2="40" style="stroke-width:10" class="w"/><line x1="242" y1="68" x2="318" y2="70" style="stroke-width:15" class="w"/>
{lbl(280,100,'Fuel','tb','middle')}{lbl(280,116,'wrist-thick and up','tm','middle')}''')

tp = ''.join(f'<line x1="{x}" y1="145" x2="{85+(x-85)*0.08:.1f}" y2="56" class="w"/>' for x in [50,74,96,110,122])
lc_tp = ''.join(f'<line x1="{x}" y1="140" x2="255" y2="88" class="w t1"/>' for x in [240,250,262,272])
svg('fire-lays', 190, 'Two fire lays: a teepee that lights fast, and a log cabin that gives steady heat and coals', f'''
<line x1="0" y1="145" x2="340" y2="145" class="m"/><line x1="170" y1="15" x2="170" y2="150" class="m t1 d"/>
<ellipse cx="85" cy="136" rx="15" ry="8" class="w wf"/>
{tp}
{flame(64,142,0.32)}
{arrow(6,124,36,124,'m','aM')}{lbl(6,114,'Wind','tm')}
{lbl(10,70,'Light it','')}{lbl(10,84,'upwind','')}{lead(40,88,60,128)}
{lbl(85,166,'Teepee','tb','middle')}{lbl(85,182,'lights fast','tm','middle')}
{lc_tp}<ellipse cx="256" cy="138" rx="12" ry="6" class="w wf"/>
<circle cx="214" cy="138" r="7" class="w wfs"/><circle cx="298" cy="138" r="7" class="w wfs"/>
<line x1="206" y1="124" x2="306" y2="124" style="stroke-width:12" class="w"/>
<circle cx="220" cy="110" r="7" class="w wfs"/><circle cx="292" cy="110" r="7" class="w wfs"/>
<line x1="212" y1="96" x2="300" y2="96" style="stroke-width:12" class="w"/>
{lbl(255,166,'Log cabin','tb','middle')}{lbl(255,182,'steady heat, coals','tm','middle')}''')

svg('fire-ferro', 160, 'Ferro rod technique: hold the striker still in the tinder and pull the rod back', f'''
<line x1="0" y1="142" x2="340" y2="142" class="m"/>
<ellipse cx="232" cy="130" rx="34" ry="12" class="w wf"/>
<path d="M216 128 c6 -8 18 -10 30 -2 M222 136 c10 4 22 2 28 -6" class="w t1"/>
<line x1="234" y1="120" x2="112" y2="40" class="st t5"/>
<line x1="112" y1="40" x2="90" y2="26" style="stroke-width:11" class="w"/>
<line x1="197" y1="115" x2="213" y2="91" class="k t5"/>
<path d="M226 118 l-6 9 M233 119 l4 10 M229 121 l0 10" class="h t1"/>
{arrow(160,100,118,72,'h','aH')}
{lbl(20,100,'Pull the rod back','tb')}
{lbl(336,40,'Striker held still,','tb','end')}{lbl(336,54,'tip in the tinder','','end')}{lead(290,58,214,94)}''')

svg('fire-platform', 150, 'A platform of green sticks keeps a fire off snow or wet ground', f'''
<rect x="0" y="112" width="340" height="38" class="snow"/>
{lbl(12,140,'Snow or wet ground','tm')}
{''.join(f'<circle cx="{x}" cy="106" r="6" class="w wfs"/>' for x in range(112, 236, 12))}
<line x1="104" y1="94" x2="240" y2="94" style="stroke-width:7" class="w"/>
{flame(170,90,1.0)}{flame(172,90,0.55,'h hf')}
{lbl(252,72,'Green sticks','tb')}{lbl(252,86,'or flat rocks','')}{lead(250,88,238,100)}''')

# ---------------- FOOD ----------------
umbel = ''.join(f'<line x1="57" y1="168" x2="{x}" y2="{140+abs(x-57)*0.25:.1f}" class="g t1"/><circle cx="{x}" cy="{140+abs(x-57)*0.25:.1f}" r="3" class="kf"/>' for x in [31,40,49,57,65,74,83])
spines = ''.join(f'<line x1="283" y1="{y}" x2="{283+(10 if i%2 else -10)}" y2="{y-6}" class="g t1"/>' for i, y in enumerate(range(34, 92, 7)))
grain = ''.join(f'<ellipse cx="{283+(5 if i%2 else -5)}" cy="{y}" rx="5" ry="8" transform="rotate({20 if i%2 else -20} {283+(5 if i%2 else -5)} {y})" class="w wf"/>' for i, y in enumerate(range(146, 196, 9)))
svg('plant-warnings', 255, 'Warning signs in unknown plants: milky sap, seeds in pods, spines or hairs, umbrella-shaped flower heads, leaves in threes, dark spurs on grain', f'''
<path d="M44 92 L52 44" class="g t3"/><path d="M48 44 l3 -6 l3 6 l3 -5" class="g t1"/>
<path d="M60 50 q8 12 2 18 q-9 2 -6 -10 z" class="k milk"/><circle cx="63" cy="78" r="3" class="k milk"/>
{lbl(57,112,'Milky sap','tb','middle')}
<path d="M132 70 C142 40 200 30 212 46 C202 62 152 82 132 70 Z" class="g gf"/>
<circle cx="152" cy="62" r="5" class="w wfs"/><circle cx="170" cy="55" r="5" class="w wfs"/><circle cx="188" cy="49" r="5" class="w wfs"/>
{lbl(170,112,'Seeds in','tb','middle')}{lbl(170,126,'pods','tb','middle')}
<line x1="283" y1="94" x2="283" y2="26" class="g t3"/>{spines}
{lbl(283,112,'Spines or','tb','middle')}{lbl(283,126,'fine hairs','tb','middle')}
<line x1="57" y1="215" x2="57" y2="168" class="g t3"/>{umbel}
<path d="M57 200 c-10 -2 -18 -8 -22 -16 M57 200 c10 -2 18 -8 22 -16 M41 192 l-6 2 M73 192 l6 2" class="g t1"/>
{lbl(57,234,'Umbrella','tb','middle')}{lbl(57,248,'flower heads','tb','middle')}
<line x1="170" y1="215" x2="170" y2="176" class="g t3"/>
<ellipse cx="170" cy="155" rx="10" ry="20" class="g gf"/>
<ellipse cx="150" cy="178" rx="10" ry="20" transform="rotate(-65 150 178)" class="g gf"/>
<ellipse cx="190" cy="178" rx="10" ry="20" transform="rotate(65 190 178)" class="g gf"/>
{lbl(170,234,'Leaves in','tb','middle')}{lbl(170,248,'threes','tb','middle')}
<line x1="283" y1="218" x2="283" y2="140" class="g t3"/>{grain}
<path d="M276 160 l-12 -8 l3 -3 z M292 178 l12 -6 l-2 -4 z M278 186 l-11 4 l1 -5 z" class="kf"/>
{lbl(283,234,'Dark spurs','tb','middle')}{lbl(283,248,'on grain','tb','middle')}''')

# ---------------- TRAPS ----------------
svg('trap-snare', 190, 'Simple snare hung over a game trail: fist-size loop about 3 inches above the trail, twigs funneling the animal in', f'''
<rect x="0" y="165" width="340" height="25" class="gr"/><line x1="0" y1="165" x2="340" y2="165" class="m"/>
<line x1="90" y1="165" x2="90" y2="34" class="w t3"/><line x1="250" y1="165" x2="250" y2="34" class="w t3"/>
<path d="M90 42 l-8 -10 M250 42 l8 -10" class="w t3"/>
<line x1="80" y1="40" x2="262" y2="40" class="w t3"/>
<line x1="132" y1="165" x2="138" y2="100" class="w"/><line x1="122" y1="165" x2="132" y2="112" class="w t1"/>
<line x1="208" y1="165" x2="202" y2="100" class="w"/><line x1="218" y1="165" x2="208" y2="112" class="w t1"/>
<line x1="170" y1="40" x2="170" y2="97" class="k t1"/>
<circle cx="170" cy="125" r="28" class="k"/>
<path d="M228 153 h14 M228 165 h14" class="m t1"/><path d="M235 155 v8" class="m t1"/>
{lbl(246,163,'≈ 3 in','tb')}
{lbl(170,24,'Wire tied to a solid support','','middle')}
{lbl(336,92,'Loop about','tb','end')}{lbl(336,106,'fist size','','end')}{lead(276,110,198,118)}
{lbl(8,90,'Twigs funnel','')}{lbl(8,104,'it into the loop','')}{lead(60,108,128,130)}''')

svg('trap-fig4', 200, 'Figure-4 deadfall: upright, diagonal lock bar and baited trigger holding up a heavy rock', f'''
<rect x="0" y="185" width="340" height="15" class="gr"/><line x1="0" y1="185" x2="340" y2="185" class="m"/>
<path d="M226 24 L240 20 L338 172 L324 184 Z" class="rock k"/>
<line x1="150" y1="185" x2="150" y2="95" class="w t5"/>
<line x1="106" y1="129" x2="252" y2="140" class="w t5"/>
<line x1="110" y1="125" x2="232" y2="33" class="w t5"/>
<path d="M146 132 h8" class="k t1"/>
<circle cx="248" cy="139" r="6" class="hf"/>
{lbl(214,18,'Heavy rock or log','tb','end')}
{lbl(192,55,'Diagonal','tb','end')}
{lbl(142,176,'Upright','tb','end')}
{lbl(222,178,'Trigger, bait on the end','','middle')}''')

def snare_on_pole(t):
    px, py = 40 + 218*t, 180 - 150*t
    nx, ny = -0.567, -0.824
    cx, cy = px + 14*nx, py + 14*ny
    return f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px+6*nx:.1f}" y2="{py+6*ny:.1f}" class="k t1"/><circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" class="k t1"/>'
svg('trap-squirrel', 190, 'Squirrel pole: several small snares fixed along a pole leaned against a tree', f'''
<rect x="256" y="0" width="30" height="190" class="w wf"/>
<line x1="0" y1="182" x2="340" y2="182" class="m"/>
<line x1="40" y1="182" x2="258" y2="30" class="w t5"/>
{snare_on_pole(0.32)}{snare_on_pole(0.52)}{snare_on_pole(0.72)}
{lbl(40,40,'Small snares along a pole','tb')}{lbl(40,54,'leaned on a tree squirrels use','')}{lead(130,60,145,92)}''')

stakes = ''
for i in range(26):
    a = math.radians(200 + i * (320/25))
    stakes += f'<circle cx="{265+40*math.cos(a):.1f}" cy="{85+40*math.sin(a):.1f}" r="2.6" class="kf"/>'
for i in range(6):
    t = i/5
    stakes += f'<circle cx="{192+t*35:.1f}" cy="{30+t*41:.1f}" r="2.6" class="kf"/><circle cx="{192+t*35:.1f}" cy="{140-t*41:.1f}" r="2.6" class="kf"/>'
svg('fishing', 175, 'Gorge hook sharpened at both ends lodges crosswise when swallowed; fish trap funnel of stakes in shallow water', f'''
<polygon points="30,50 80,45 130,50 80,55" class="w wfs"/>
<line x1="80" y1="48" x2="80" y2="14" class="k t1"/>
{lbl(80,76,'Sharpened both ends,','','middle')}{lbl(80,90,'tied in the middle','','middle')}
<path d="M30 140 C50 112 110 110 136 128 L156 116 L152 140 L156 164 L136 152 C110 170 50 168 30 140 Z" class="k"/>
<circle cx="44" cy="134" r="2.5" class="kf"/>
<line x1="62" y1="124" x2="62" y2="156" class="w t3"/>
<line x1="30" y1="140" x2="10" y2="110" class="k t1"/>
{lbl(92,170,'Lodges crosswise','tm','middle')}
<line x1="175" y1="15" x2="175" y2="160" class="m t1 d"/>
<rect x="182" y="18" width="158" height="134" class="af"/>
{stakes}
{arrow(330,138,298,138,'a','aA')}{lbl(334,166,'Current','tm','end')}
<path d="M188 85 C200 85 215 85 240 85" class="k t1 d" marker-end="url(#aK)"/>
{lbl(262,90,'Trap','tb','middle')}''')

# ---------------- FIELD DRESSING ----------------
svg('dress-deer', 240, 'Field dressing from above, animal on its back: cut from pelvis to breastbone, free the diaphragm, cut the windpipe, cut around and tie off the anus', f'''
<ellipse cx="170" cy="20" rx="13" ry="15" class="k"/>
<path d="M162 34 L158 46 M178 34 L182 46" class="k"/>
<path d="M150 44 C118 62 112 112 118 160 C122 196 140 210 170 212 C200 210 218 196 222 160 C228 112 222 62 190 44 Z" class="k"/>
<path d="M134 72 L100 54 M206 72 L240 54 M130 188 L98 216 M210 188 L242 216" class="k t3"/>
{arrow(30,80,30,26,'k','aK')}{lbl(40,56,'Head uphill','tb')}
<line x1="170" y1="190" x2="170" y2="72" class="h t3 d"/>
<path d="M128 100 Q170 84 212 100" class="a"/>
<circle cx="170" cy="203" r="5" class="h"/>
<line x1="170" y1="36" x2="170" y2="46" class="h t3"/>
{lbl(232,40,'Windpipe: cut as','')}{lbl(232,54,'far forward as you can','')}{lead(230,46,176,42)}
{lbl(232,96,'Diaphragm: cut it','')}{lbl(232,110,'away from the ribs','')}{lead(230,102,212,100)}
{lbl(232,144,'Shallow cut, blade','tb')}{lbl(232,158,'edge up, breastbone','')}{lbl(232,172,'to pelvis','')}{lead(230,150,174,140)}
{lbl(232,206,'Cut around, tie off','')}{lead(230,204,176,203)}''')

svg('dress-fish', 110, 'Gut a fish by cutting from the vent to the gills', f'''
<path d="M40 55 C70 20 200 16 260 50 L310 24 L300 55 L310 86 L260 60 C200 94 70 90 40 55 Z" class="k"/>
<circle cx="64" cy="50" r="3" class="kf"/><path d="M92 34 Q104 55 92 76" class="k t1"/>
<path d="M216 72 Q150 84 96 72" class="h t3 d"/>
<circle cx="218" cy="71" r="3" class="h"/>
{lbl(160,104,'Cut from the vent to the gills, pull the guts out','','middle')}''')

# ---------------- NAVIGATION ----------------
svg('nav-shadow', 195, 'Shadow-stick method: first shadow-tip mark is west, second is east; north is perpendicular', f'''
<circle cx="170" cy="168" r="5" class="kf"/>{lbl(180,184,'Stick','tm')}
<line x1="170" y1="168" x2="112" y2="80" class="m t3"/><line x1="170" y1="168" x2="228" y2="84" class="m t1 d"/>
<line x1="70" y1="78" x2="262" y2="86" class="h" marker-end="url(#aH)"/>
<circle cx="112" cy="80" r="6" class="k kf"/><circle cx="228" cy="84" r="6" class="k kf"/>
{lbl(112,104,'1st mark','tb','end')}{lbl(234,106,'2nd mark,','tb')}{lbl(234,120,'15+ min later','')}
{lbl(62,82,'W','tl','end')}{lbl(270,90,'E','tl')}
<line x1="168" y1="80" x2="170" y2="18" class="a" marker-end="url(#aA)"/>{lbl(178,26,'North','tl')}''')

ticks = ''.join(f'<line x1="{110+66*math.sin(math.radians(a)):.1f}" y1="{105-66*math.cos(math.radians(a)):.1f}" x2="{110+74*math.sin(math.radians(a)):.1f}" y2="{105-74*math.cos(math.radians(a)):.1f}" class="k {"t3" if a%90==0 else "t1"}"/>' for a in range(0, 360, 30))
svg('nav-watch', 210, 'Watch method, Northern Hemisphere: point the hour hand at the sun; south is halfway to 12 o’clock', f'''
<circle cx="110" cy="105" r="78" class="k"/>{ticks}
{lbl(110,52,'12','tb','middle')}
<line x1="110" y1="105" x2="157.6" y2="132.5" class="k t5"/>
<line x1="110" y1="105" x2="110" y2="44" class="m t1 d"/>
<line x1="160" y1="134" x2="200" y2="157" class="h d t1"/>{sun(208,162,9)}
<line x1="36" y1="148" x2="186" y2="61" class="a" marker-end="url(#aA)"/>
{lbl(190,56,'South','tl')}{lbl(28,166,'North','tm')}
{lbl(222,96,'Northern','tb')}{lbl(222,110,'Hemisphere:','tb')}{lbl(222,128,'hour hand at the sun,')}{lbl(222,142,'south is halfway')}{lbl(222,156,'to 12 o’clock.')}
{lbl(222,176,'In daylight saving','tm')}{lbl(222,190,'time, use 1 o’clock.','tm')}''')

stars = [(35,140),(65,128),(92,135),(120,145),(178,152),(150,165),(115,170)]
svg('nav-polaris', 222, 'Find Polaris by extending the Big Dipper’s pointer stars about five times their spacing', f'''
<path d="M35 140 L65 128 L92 135 L120 145 L178 152 L150 165 L115 170 L120 145" class="m t1"/>
{''.join(f'<circle cx="{x}" cy="{y}" r="3.6" class="kf"/>' for x, y in stars)}
<line x1="182" y1="150" x2="312" y2="90" class="a d" marker-end="url(#aA)"/>
<circle cx="318" cy="87" r="5.5" class="kf"/>
{lbl(312,72,'Polaris (North Star)','tb','end')}
{lbl(246,136,'5× the gap','')}
{lbl(70,192,'Big Dipper','tb','middle')}{lbl(168,188,'Pointer stars','','middle')}
<line x1="0" y1="206" x2="340" y2="206" class="m"/><line x1="318" y1="94" x2="318" y2="206" class="m d t1"/>
{lbl(310,200,'North','tl','end')}''')

svg('nav-cross', 290, 'Southern Cross: extend the long axis about four and a half times, then drop to the horizon for south', f'''
<line x1="40" y1="40" x2="75" y2="70" class="m t1"/><line x1="67" y1="44" x2="48" y2="66" class="m t1"/>
<circle cx="40" cy="40" r="3.6" class="kf"/><circle cx="75" cy="70" r="4.2" class="kf"/><circle cx="67" cy="44" r="3.8" class="kf"/><circle cx="48" cy="66" r="3" class="kf"/>
<line x1="80" y1="74" x2="228" y2="201" class="a d" marker-end="url(#aA)"/>
<circle cx="151" cy="44" r="4" class="kf"/><circle cx="184" cy="31" r="4.6" class="kf"/>
<line x1="167" y1="38" x2="230" y2="198" class="m t1 d"/>
<circle cx="232" cy="205" r="6" class="a"/>
{lbl(20,100,'Southern Cross','tb')}{lbl(196,30,'Pointers','')}
{lbl(140,150,'4½ × its length','','end')}
{lbl(246,196,'South','')}{lbl(246,210,'celestial pole','')}
<line x1="0" y1="270" x2="340" y2="270" class="m"/><line x1="232" y1="212" x2="232" y2="270" class="m d t1"/>
{lbl(232,286,'South','tl','middle')}''')

svg('nav-hand', 180, 'Daylight left: each finger width between the sun and horizon at arm’s length is about 15 minutes', f'''
<rect x="0" y="150" width="340" height="30" class="gr"/><line x1="0" y1="150" x2="340" y2="150" class="m"/>
{sun(232,38,12)}
{''.join(f'<rect x="168" y="{56+i*23.5:.1f}" width="126" height="21" rx="10" class="skin"/>' for i in range(4))}
{''.join(lbl(300, 70+i*23.5, f'{(i+1)*15}', 'tm') for i in range(3))}{lbl(300,140.5,'60 min','tm')}
{lbl(16,84,'Arm’s length:','tb')}{lbl(16,100,'each finger ≈ 15 min')}{lbl(16,116,'4 fingers ≈ 1 hour')}''')

svg('nav-aimoff', 200, 'Aiming off: aim to one side of a point on a river so you know which way to turn when you reach it', f'''
<path d="M0 56 C60 40 100 72 170 54 S280 40 340 56" class="a t5"/>
<rect x="196" y="38" width="12" height="12" class="hf"/>{lbl(202,30,'Camp','tb','middle')}
<circle cx="200" cy="180" r="6" class="kf"/>{lbl(212,186,'You','tb')}
<line x1="200" y1="174" x2="202" y2="56" class="m d t1"/>
<line x1="198" y1="174" x2="134" y2="66" class="k" marker-end="url(#aK)"/>
<path d="M140 60 C160 58 172 54 190 50" class="h t3" marker-end="url(#aH)"/>
{lbl(150,132,'Aim off to one side','tb','end')}
{lbl(212,98,'Hit the river,','')}{lbl(212,112,'then turn toward camp','')}''')

# ---------------- SIGNALS ----------------
svg('signal-ground', 150, 'Ground-to-air signals: V means need assistance, X means need medical help; three fires in a triangle means distress', f'''
<rect x="0" y="34" width="168" height="94" class="gr"/>
<path d="M22 46 L48 118 L74 46" class="k" style="stroke-width:10"/>
<path d="M98 46 L150 118 M150 46 L98 118" class="k" style="stroke-width:10"/>
{lbl(48,144,'V: need help','tb','middle')}{lbl(124,144,'X: medical','tb','middle')}
{lbl(84,22,'Big, high contrast','tm','middle')}
<line x1="178" y1="20" x2="178" y2="140" class="m t1 d"/>
{flame(220,120,0.6)}{flame(306,120,0.6)}{flame(263,68,0.6)}
<path d="M220 112 L306 112 L263 60 Z" class="m d t1"/>
{lbl(262,144,'3 fires in a triangle','tb','middle')}''')

svg('signal-mirror', 170, 'Signal mirror: hold it under your eye, sight the aircraft through a V of two fingers, tilt until the light hits your fingers', f'''
{sun(30,28,10)}
<line x1="40" y1="40" x2="62" y2="106" class="h d t1"/>
<polygon points="52,110 70,104 74,118 56,124" class="k af"/>
<line x1="64" y1="113" x2="290" y2="57" class="h" marker-end="url(#aH)"/>
<path d="M193 132 L182 78 M193 132 L206 80" class="skin-s"/>
<circle cx="194" cy="138" r="9" class="skin"/>
<path d="M286 58 L322 49 M300 40 L308 68" class="k t3"/>
{lbl(84,146,'Mirror under your eye','tb')}
{lbl(214,128,'Sight the aircraft','')}{lbl(214,142,'through 2 fingers','')}''')

# ---------------- KNOTS ----------------
def offset(pts, dx, dy=0):
    return [(x+dx, y+dy, z) for x, y, z in pts]
S = [(55,8,0),(55,45,0),(55,64,-1),(78,80,0),(58,106,1),(32,92,0),(35,72,0),(55,64,1),(74,60,0)]
BIG = [(86,85,0),(88,150,0),(62,198,0),(28,165,0),(30,125,0)]
UP = [(43,108,-1),(44,88,0),(44,70,2),(45,48,1)]
COLLAR = [(48,32,0),(56,25,-2),(64,32,0),(66,48,1),(65,63,2),(64,84,0),(63,104,-1),(64,124,0)]
p1 = S + [(86,85,0),(88,140,0),(86,170,0)]
p2 = S + BIG + UP[:-1] + [(45,46,1)]
p3 = S + BIG + UP + COLLAR
body = rope_svg([(offset(p1, 0, 10), 'rp')]) + rope_svg([(offset(p2, 113, 10), 'rp')]) + rope_svg([(offset(p3, 226, 10), 'rp')])
svg('knot-bowline', 245, 'Bowline in three steps: small loop with the working side on top; end up through the loop; around behind the standing part and back down through the loop', f'''
{body}
{''.join(f'<circle cx="{14+113*i}" cy="20" r="10" class="k"/>' + lbl(14+113*i, 24, str(i+1), 'tb', 'middle') for i in range(3))}
{lbl(56,236,'Small loop,','','middle')}{lbl(56,222,'','')}
{lbl(169,236,'Up through it','','middle')}{lbl(282,236,'Around, back down','','middle')}
{lbl(56,222,'Working side on top','tm','middle')}''')

trk = rope_svg([([(40,22,0),(120,48,0),(196,74,0),(212,86,1),(205,100,0),(196,92,-1),(194,104,0),(214,140,0),(246,168,0),(262,160,-1),(256,140,0),(222,100,0),(204,86,-1),(194,70,0),(214,62,2),(240,96,1),(282,150,0),(300,170,0)], 'rp')])
svg('knot-trucker', 190, 'Trucker’s hitch: a fixed loop in the line, the end around the anchor point and back up through the loop, then pulled down and tied off', f'''
<circle cx="34" cy="20" r="9" class="k"/>
<path d="M240 172 q6 -10 14 -4 q10 8 -2 18" class="k t3"/><line x1="226" y1="186" x2="290" y2="186" class="k t3"/>
{trk}
{arrow(310,150,326,180,'h','aH')}
{lbl(14,46,'Anchor','tb')}
{lbl(232,40,'Fixed loop','tb')}{lbl(232,54,'in the line','')}
{lbl(110,150,'Around the hook,','','start')}{lbl(110,164,'back up through','')}{lbl(110,178,'the loop','')}
{lbl(336,140,'Pull,','tb','end')}{lbl(336,154,'then tie off','','end')}''')

# ---------------- NEW SECTIONS ----------------
svg('lightning', 150, 'Count from flash to thunder: every 5 seconds is about 1 mile. If you can hear thunder you can be struck. Wait 30 minutes after the last thunder.', f'''
<path d="M20 58 C8 58 6 40 20 36 C20 20 42 14 52 26 C60 10 90 12 94 30 C110 28 116 50 102 58 Z" class="gr m"/>
<polygon points="60,58 46,96 60,96 50,134 82,86 66,86 78,58" class="hf"/>
<path d="M112 70 q10 20 0 40 M124 62 q14 28 0 56 M136 54 q18 36 0 72" class="m t1"/>
{lbl(160,34,'Count flash to thunder:','tb')}{lbl(160,50,'5 seconds ≈ 1 mile')}
{lbl(160,76,'Hear thunder? You’re','tb')}{lbl(160,92,'close enough to be struck.')}
{lbl(160,118,'Wait 30 minutes after','tb')}{lbl(160,134,'the last thunder.')}''')

svg('tick', 150, 'Remove a tick with fine-tipped tweezers gripped at the skin, pulling straight up with steady pressure', f'''
<rect x="0" y="102" width="340" height="48" class="skin"/>
<path d="M0 102 C60 98 120 106 170 102 S280 98 340 102" class="w"/>
<ellipse cx="170" cy="84" rx="18" ry="13" class="kf"/>
<path d="M156 80 l-12 -6 M156 88 l-14 2 M184 80 l12 -6 M184 88 l14 2 M160 94 l-8 8 M180 94 l8 8" class="k t1"/>
<line x1="170" y1="96" x2="170" y2="106" class="k t3"/>
<path d="M112 14 L166 100 M146 8 L174 100" class="st t3"/>
{arrow(226,92,226,26,'h','aH')}
{lbl(236,44,'Pull straight up,','tb')}{lbl(236,58,'steady pressure')}
{lbl(236,128,'Grip right at the skin','tb')}{lead(234,124,176,102)}
{lbl(10,128,'Don’t twist or','tm')}{lbl(10,142,'squeeze the body','tm')}''')

svg('river', 200, 'River crossing: face upstream, pole planted upstream, shuffle across angling slightly downstream, away from strainers', f'''
<rect x="0" y="40" width="340" height="128" class="af"/>
<line x1="0" y1="40" x2="340" y2="40" class="m"/><line x1="0" y1="168" x2="340" y2="168" class="m"/>
{arrow(14,70,54,70,'a','aA')}{arrow(14,140,54,140,'a','aA')}{lbl(14,62,'Current','tm')}
<path d="M140 30 C150 80 168 120 196 178" class="k d" marker-end="url(#aK)"/>
<circle cx="164" cy="104" r="8" class="kf"/>
<line x1="156" y1="102" x2="128" y2="94" class="w t3"/>
<path d="M272 58 L330 122 M290 70 l-10 12 M306 88 l12 -8 M318 104 l-12 10" class="w t3"/>
{lbl(120,124,'Face upstream,','tb','end')}{lbl(120,138,'pole upstream','','end')}
{lbl(330,148,'Strainers and rapids:','tb','end')}{lbl(330,162,'stay well upstream','','end')}
{lbl(140,24,'Angle slightly downstream','')}''')

icons = [
 ('Map, compass', '<circle cx="0" cy="0" r="16" class="k"/><path d="M0 -12 L5 0 L0 12 L-5 0 Z" class="k"/><path d="M0 -12 L5 0 L-5 0 Z" class="hf"/>'),
 ('Headlamp', '<path d="M-18 0 C-18 -14 18 -14 18 0" class="k t3"/><rect x="-8" y="-6" width="16" height="12" rx="3" class="k"/><path d="M8 0 L20 -6 M8 0 L22 2" class="h t1"/>'),
 ('Sun cover', '<circle cx="0" cy="0" r="7" class="h hfl"/>' + ''.join(f'<line x1="{11*math.cos(a):.1f}" y1="{11*math.sin(a):.1f}" x2="{16*math.cos(a):.1f}" y2="{16*math.sin(a):.1f}" class="h"/>' for a in [i*math.pi/4 for i in range(8)])),
 ('First aid', '<rect x="-16" y="-14" width="32" height="28" rx="4" class="k"/><path d="M0 -8 V8 M-8 0 H8" class="h t3"/>'),
 ('Knife', '<path d="M-18 6 L8 -6 Q18 -10 16 -2 L-2 8 Z" class="k"/><line x1="-18" y1="6" x2="-24" y2="10" class="w t5"/>'),
 ('Fire', flame(0, 16, 0.65)),
 ('Shelter', '<path d="M-20 14 L0 -14 L20 14 Z M0 -14 L0 14" class="k"/>'),
 ('Extra food', '<rect x="-16" y="-8" width="32" height="16" rx="3" class="k"/><path d="M-10 -8 V8 M10 -8 V8" class="k t1"/>'),
 ('Extra water', '<rect x="-9" y="-10" width="18" height="26" rx="4" class="k"/><rect x="-5" y="-16" width="10" height="6" class="k"/><path d="M-9 2 H9" class="a"/>'),
 ('Extra layers', '<path d="M-8 -14 L-20 -6 L-14 4 L-10 0 V16 H10 V0 L14 4 L20 -6 L8 -14 Q0 -8 -8 -14 Z" class="k"/>'),
]
grid = ''
for i, (name, ic) in enumerate(icons):
    cx, cy = 34 + 68*(i % 5), 34 + 92*(i // 5)
    grid += f'<g transform="translate({cx} {cy})">{ic}</g>' + lbl(cx, cy + 40, name, '', 'middle')
svg('kit', 186, 'The ten essentials: navigation, headlamp, sun protection, first aid, knife, fire, shelter, extra food, extra water, extra layers', grid)

# ---------------- REVISIONS (override earlier drafts) ----------------
svg('dress-deer', 240, 'Field dressing from above, animal on its back: cut from pelvis to breastbone, free the diaphragm, cut the windpipe, cut around and tie off the anus', f'''
<g transform="translate(-58 0)">
<ellipse cx="170" cy="20" rx="13" ry="15" class="k"/>
<path d="M162 34 L158 46 M178 34 L182 46" class="k"/>
<path d="M150 44 C118 62 112 112 118 160 C122 196 140 210 170 212 C200 210 218 196 222 160 C228 112 222 62 190 44 Z" class="k"/>
<path d="M134 72 L106 56 M206 72 L234 56 M130 188 L104 214 M210 188 L236 214" class="k t3"/>
<line x1="170" y1="190" x2="170" y2="72" class="h t3 d"/>
<path d="M128 100 Q170 84 212 100" class="a"/>
<circle cx="170" cy="203" r="5" class="h"/>
<line x1="170" y1="36" x2="170" y2="46" class="h t3"/>
</g>
{arrow(16,130,16,70,'k','aK')}{lbl(10,150,'Head','tb')}{lbl(10,164,'uphill','tb')}
{lbl(206,30,'Windpipe: cut','tb')}{lbl(206,44,'far forward')}{lead(204,38,118,40)}
{lbl(206,90,'Diaphragm: free','tb')}{lbl(206,104,'it from the ribs')}{lead(204,98,156,98)}
{lbl(206,140,'Shallow cut,','tb')}{lbl(206,154,'blade edge up,')}{lbl(206,168,'breastbone to pelvis')}{lead(204,146,116,140)}
{lbl(206,200,'Cut around the','tb')}{lbl(206,214,'anus, tie it off')}{lead(204,206,118,203)}''')

svg('nav-watch', 210, 'Watch method, Northern Hemisphere: point the hour hand at the sun; south is halfway to 12 o’clock', f'''
<circle cx="100" cy="105" r="78" class="k"/>{''.join(f'<line x1="{100+66*math.sin(math.radians(a)):.1f}" y1="{105-66*math.cos(math.radians(a)):.1f}" x2="{100+74*math.sin(math.radians(a)):.1f}" y2="{105-74*math.cos(math.radians(a)):.1f}" class="k {"t3" if a%90==0 else "t1"}"/>' for a in range(0, 360, 30))}
{lbl(100,52,'12','tb','middle')}
<line x1="100" y1="105" x2="147.6" y2="132.5" class="k t5"/>
<line x1="100" y1="105" x2="100" y2="44" class="m t1 d"/>
<line x1="150" y1="134" x2="186" y2="155" class="h d t1"/>{sun(194,160,9)}
<line x1="26" y1="148" x2="176" y2="61" class="a" marker-end="url(#aA)"/>
{lbl(178,52,'South','tl')}{lbl(18,170,'North','tm')}
{lbl(222,86,'Northern','tb')}{lbl(222,100,'Hemisphere','tb')}{lbl(222,118,'Hour hand at sun.')}{lbl(222,132,'South is halfway')}{lbl(222,146,'to 12 o’clock.')}
{lbl(222,170,'Daylight saving:','tm')}{lbl(222,184,'use 1 o’clock.','tm')}''')

svg('nav-hand', 180, 'Daylight left: each finger width between the sun and horizon at arm’s length is about 15 minutes', f'''
<rect x="0" y="150" width="340" height="30" class="gr"/><line x1="0" y1="150" x2="340" y2="150" class="m"/>
{sun(222,38,12)}
{''.join(f'<rect x="160" y="{56+i*23.5:.1f}" width="124" height="21" rx="10" class="skin"/>' for i in range(4))}
{''.join(lbl(292, 71+i*23.5, f'{(i+1)*15} min' if i < 3 else '1 hr', 'tm') for i in range(4))}
{lbl(16,84,'Arm’s length:','tb')}{lbl(16,100,'each finger ≈ 15 min')}{lbl(16,116,'4 fingers ≈ 1 hour')}''')

svg('nav-aimoff', 200, 'Aiming off: aim to one side of a point on a river so you know which way to turn when you reach it', f'''
<path d="M0 56 C60 40 100 72 170 54 S280 40 340 56" class="a t5"/>
<rect x="196" y="38" width="12" height="12" class="hf"/>{lbl(202,30,'Camp','tb','middle')}
<circle cx="200" cy="180" r="6" class="kf"/>{lbl(212,186,'You','tb')}
<line x1="200" y1="174" x2="202" y2="56" class="m d t1"/>
<line x1="198" y1="174" x2="134" y2="66" class="k" marker-end="url(#aK)"/>
<path d="M140 60 C160 58 172 54 190 50" class="h t3" marker-end="url(#aH)"/>
{lbl(150,132,'Aim off to one side','tb','end')}
{lbl(214,98,'Hit the river,')}{lbl(214,112,'turn toward camp')}''')

svg('signal-ground', 150, 'Ground-to-air signals: V means need assistance, X means need medical help; three fires in a triangle means distress', f'''
<rect x="0" y="34" width="168" height="94" class="gr"/>
<path d="M22 46 L48 118 L74 46" class="k" style="stroke-width:10"/>
<path d="M98 46 L150 118 M150 46 L98 118" class="k" style="stroke-width:10"/>
{lbl(48,144,'V = help','tb','middle')}{lbl(124,144,'X = medical','tb','middle')}
{lbl(84,22,'Big, high contrast','tm','middle')}
<line x1="178" y1="20" x2="178" y2="140" class="m t1 d"/>
{flame(220,120,0.6)}{flame(306,120,0.6)}{flame(263,68,0.6)}
<path d="M220 112 L306 112 L263 60 Z" class="m d t1"/>
{lbl(262,144,'3 fires in a triangle','tb','middle')}''')

svg('signal-mirror', 170, 'Signal mirror: hold it under your eye, sight the aircraft through a V of two fingers, tilt until the light hits your fingers', f'''
{sun(30,28,10)}
<line x1="40" y1="40" x2="62" y2="106" class="h d t1"/>
<polygon points="52,110 70,104 74,118 56,124" class="k af"/>
<line x1="64" y1="113" x2="290" y2="57" class="h" marker-end="url(#aH)"/>
<path d="M193 132 L182 78 M193 132 L206 80" class="skin-s"/>
<circle cx="194" cy="138" r="9" class="skin"/>
<path d="M286 58 L322 49 M300 40 L308 68" class="k t3"/>
{lbl(10,152,'Mirror under your eye','tb')}
{lbl(216,128,'Sight the aircraft','')}{lbl(216,142,'through 2 fingers','')}''')

S = [(55,8,0),(55,45,0),(55,64,-1),(74,84,0),(56,108,1),(30,94,0),(33,72,0),(55,64,1),(78,58,0)]
BIG = [(94,80,0),(96,150,0),(66,200,0),(28,166,0),(30,126,0)]
UP = [(43,110,-1),(44,90,0),(44,70,2),(45,48,1)]
COLLAR = [(48,32,0),(56,24,-2),(64,32,0),(66,48,1),(65,63,2),(64,84,0),(63,106,-1),(64,126,0)]
p1 = S + [(94,80,0),(96,140,0),(94,176,0)]
p2 = S + BIG + UP[:-1] + [(45,46,1)]
p3 = S + BIG + UP + COLLAR
body = rope_svg([(offset(p1, 0, 26), 'rp')]) + rope_svg([(offset(p2, 113, 26), 'rp')]) + rope_svg([(offset(p3, 226, 26), 'rp')])
svg('knot-bowline', 270, 'Bowline in three steps: small loop with the working side on top; end up through the loop; around behind the standing part and back down through the loop', f'''
{body}
{''.join(f'<circle cx="{14+113*i}" cy="16" r="10" class="k"/>' + lbl(14+113*i, 20, str(i+1), 'tb', 'middle') for i in range(3))}
{lbl(56,248,'Small loop,','tb','middle')}{lbl(56,262,'end side on top','tm','middle')}
{lbl(169,248,'End up through','tb','middle')}{lbl(169,262,'from below','tm','middle')}
{lbl(282,248,'Around back,','tb','middle')}{lbl(282,262,'down through','tm','middle')}''')

ring = [(206+11*math.cos(math.radians(a)), 92+11*math.sin(math.radians(a)), (1 if 30 < a < 150 else -1)) for a in range(0, 361, 30)]
trk = rope_svg([([(40,28,0),(120,52,0),(194,76,0)], 'rp'),
                ([(196,76,0),(214,108,0),(236,150,0),(240,168,0),(248,176,0),(256,170,0),(254,152,0),(228,118,0),(210,100,1),(205,88,0),(204,78,-1),(212,72,0),(222,80,0),(256,120,0),(296,162,0)], 'rp'),
                (ring, 'rp')], width=6)
svg('knot-trucker', 205, 'Trucker’s hitch: a fixed loop in the line, the end around the hook and back up through the loop, then pulled tight and tied off', f'''
<circle cx="34" cy="22" r="9" class="k"/>
<path d="M232 186 h40 M252 186 v-10 q0 -8 -6 -8" class="k t3"/>
{trk}
{arrow(298,166,316,192,'h','aH')}
{lbl(14,48,'Anchor','tb')}
{lbl(226,48,'Fixed loop','tb')}{lbl(226,62,'in the line','')}{lead(224,58,212,84)}
{lbl(80,132,'Down around the hook,','')}{lbl(80,146,'back up through the loop','')}
{lbl(336,128,'Pull,','tb','end')}{lbl(336,142,'then tie off','','end')}''')

svg('tick', 150, 'Remove a tick with fine-tipped tweezers gripped at the skin, pulling straight up with steady pressure', f'''
<rect x="0" y="102" width="340" height="48" class="skin"/>
<path d="M0 102 C60 98 120 106 170 102 S280 98 340 102" class="w"/>
<ellipse cx="150" cy="84" rx="18" ry="13" class="kf"/>
<path d="M136 80 l-12 -6 M136 88 l-14 2 M164 80 l12 -6 M164 88 l14 2 M140 94 l-8 8 M160 94 l8 8" class="k t1"/>
<line x1="150" y1="96" x2="150" y2="106" class="k t3"/>
<path d="M92 14 L146 100 M126 8 L154 100" class="st t3"/>
{arrow(206,92,206,26,'h','aH')}
{lbl(218,44,'Pull straight up,','tb')}{lbl(218,58,'steady pressure')}
{lbl(218,128,'Grip right at','tb')}{lbl(218,142,'the skin','tb')}{lead(216,126,156,103)}
{lbl(10,128,'Don’t twist or','tm')}{lbl(10,142,'squeeze the body','tm')}''')

icons2 = [('Navigation',)+icons[0][1:], ('Headlamp',)+icons[1][1:], ('Sun',)+icons[2][1:], ('First aid',)+icons[3][1:], ('Knife',)+icons[4][1:],
          ('Fire',)+icons[5][1:], ('Shelter',)+icons[6][1:], ('Food',)+icons[7][1:], ('Water',)+icons[8][1:], ('Layers',)+icons[9][1:]]
grid = ''
for i, (name, ic) in enumerate(icons2):
    cx, cy = 34 + 68*(i % 5), 34 + 92*(i // 5)
    grid += f'<g transform="translate({cx} {cy})">{ic}</g>' + lbl(cx, cy + 40, name, '', 'middle')
svg('kit', 186, 'The ten essentials: navigation, headlamp, sun protection, first aid, knife, fire, shelter, extra food, extra water, extra layers', grid)

svg('knot-trucker', 205, 'Trucker’s hitch: a fixed loop in the line, the end around the hook and back up through the loop, then pulled tight and tied off', f'''
<circle cx="30" cy="28" r="9" class="k"/>
<line x1="38" y1="32" x2="178" y2="78" class="w t3"/>
<rect x="174" y="72" width="14" height="12" rx="4" class="w wfs"/>
<ellipse cx="192" cy="100" rx="9" ry="15" class="w t3"/>
<line x1="180" y1="84" x2="234" y2="176" class="w t3"/>
<path d="M232 190 h36 M250 190 v-12 q0 -8 -8 -8 q-8 0 -8 8" class="k t3"/>
<line x1="258" y1="176" x2="196" y2="110" class="w t3"/>
<path d="M194 90 C204 70 226 74 246 104 L300 170" class="w t3"/>
{arrow(300,170,316,194,'h','aH')}
{lbl(14,56,'Anchor','tb')}
{lbl(214,48,'Fixed loop','tb')}{lbl(214,62,'in the line','')}{lead(212,58,198,86)}
{lbl(14,142,'Down around the hook,','')}{lbl(14,156,'back up through the loop','')}{lead(166,148,214,140)}
{lbl(336,124,'Pull down,','tb','end')}{lbl(336,138,'then tie off','','end')}''')
