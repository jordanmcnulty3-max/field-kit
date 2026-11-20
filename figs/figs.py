from rope import rope_svg
import math
F = {}
def svg(name, h, label, body, w=340):
    if name in F:
        raise ValueError(f'duplicate figure id: {name}')
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

svg('water-safe', 182, 'Rolling boil for at least 1 minute, or 3 minutes above 5,000 feet; or, with no fire, add 8 drops of 5% to 9% unscented bleach per gallon, stir and wait 30 minutes', f'''
{lbl(80,20,'Rolling boil','tb','middle')}
<path d="M30 80 H130 V140 Q130 150 120 150 H40 Q30 150 30 140 Z" class="k"/>
<path d="M30 90 H18 M130 90 H142" class="k t3"/>
<path d="M34 98 H126" class="a"/>
<circle cx="55" cy="115" r="4" class="a t1"/><circle cx="80" cy="108" r="3" class="a t1"/><circle cx="102" cy="121" r="5" class="a t1"/><circle cx="68" cy="133" r="3" class="a t1"/><circle cx="112" cy="138" r="3" class="a t1"/>
<path d="M60 76 q-5 -6 0 -11 M100 76 q-5 -6 0 -11" class="m t1"/>
{flame(55,170,0.42)}{flame(80,170,0.5)}{flame(105,170,0.42)}
{lbl(80,46,'At least 1 minute','','middle')}{lbl(80,62,'3 min above 5,000 ft','tm','middle')}
<line x1="170" y1="20" x2="170" y2="160" class="m t1 d"/>
{lbl(260,20,'No fire? Bleach','tb','middle')}
<g transform="translate(0,8)">
<rect x="196" y="76" width="40" height="66" rx="6" class="k"/><rect x="207" y="62" width="18" height="14" class="k"/><rect x="204" y="54" width="24" height="8" rx="2" class="k kf"/>
<path d="M254 82 q6 9 0 14 q-6 -5 0 -14z M254 102 q6 9 0 14 q-6 -5 0 -14z M254 122 q6 9 0 14 q-6 -5 0 -14z" class="afs"/>
<path d="M276 92 h44 a6 6 0 0 1 6 6 v44 a6 6 0 0 1 -6 6 h-44 a6 6 0 0 1 -6 -6 v-44 a6 6 0 0 1 6 -6z" class="k"/>
<path d="M286 92 v-12 h20 v12" class="k"/><path d="M272 116 H324" class="a"/>
{lbl(298,138,'1 gal','tm','middle')}
</g>
{lbl(260,32,'8 drops of 5% to 9%','','middle')}{lbl(260,44,'unscented bleach','','middle')}{lbl(260,56,'per gallon','','middle')}
{lbl(260,174,'Stir, wait 30 minutes','tb','middle')}''')


def badge(cx, cy, n):
    return f'<circle cx="{cx}" cy="{cy}" r="9" class="k milk"/>{lbl(cx, cy+4, n, "tb", "middle")}'
def dim(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="m" marker-start="url(#aM)" marker-end="url(#aM)"/>'

# Labels fixed by the content reviewer (water heater), in this order.
heater_rows = [(40, ['Power or gas OFF']), (82, ['Let it cool']), (124, ['Close the water', 'intake valve']),
               (172, ['Open a hot tap']), (214, ['Container here']), (256, ['Open the drain'])]
heater_list = ''.join(badge(184, y - 4, i) + ''.join(lbl(200, y + 14 * j, t) for j, t in enumerate(rows))
                      for i, (y, rows) in enumerate(heater_rows, 1))
svg('water-heater-drain', 324, 'Water heater tank drained in six steps: 1 Power or gas OFF; 2 Let it cool; 3 Close the water intake valve; 4 Open a hot tap; 5 Container here; 6 Open the drain. Refill the tank before turning power or gas back on.', f'''
<line x1="6" y1="268" x2="160" y2="268" class="m"/>
<line x1="38" y1="216" x2="38" y2="232" class="k t3"/><line x1="86" y1="216" x2="86" y2="232" class="k t3"/>
<rect x="28" y="66" width="68" height="150" rx="12" class="k t3"/>
<rect x="31" y="150" width="62" height="63" rx="9" class="af"/>
<path d="M44 90 q-5 -6 0 -11 M62 90 q-5 -6 0 -11 M80 90 q-5 -6 0 -11" class="h"/>
<rect x="10" y="170" width="18" height="24" rx="3" class="k milk"/><circle cx="19" cy="182" r="4" class="k"/>
<path d="M44 66 V12" class="k t5"/>
<path d="M36 34 V50 L52 34 V50 Z" class="k milk"/>
<path d="M80 66 V24 H128" class="k t5"/>
<path d="M126 24 H150 V36 M139 24 V12 M131 12 H147" class="k t3"/>
<line x1="150" y1="42" x2="150" y2="70" class="a t3 d"/>
<path d="M96 200 H120 V214" class="k t3"/>
<path d="M104 194 V206 L112 194 V206 Z" class="k milk"/>
<circle cx="120" cy="226" r="3" class="afs"/>
<path d="M96 240 L100 268 H142 L146 240 Z" class="k"/><path d="M98 254 H144" class="a"/>
{badge(19, 158, 1)}{badge(62, 122, 2)}{badge(20, 42, 3)}{badge(128, 54, 4)}{badge(80, 252, 5)}{badge(128, 190, 6)}
{heater_list}
<line x1="6" y1="282" x2="334" y2="282" class="m t1"/>
{lbl(6,300,'Refill the tank before turning','tb')}{lbl(6,314,'power or gas back on','tb')}''')

svg('toilet-buckets', 186, 'Two-bucket toilet: a lidded pee bucket and a poo bucket with the toilet seat on it; cover material, about half a cup (120 mL), after each poo', f'''
<line x1="6" y1="172" x2="334" y2="172" class="m"/>
<path d="M24 98 L32 172 H88 L96 98" class="k t3"/>
<path d="M20 98 H100 Q100 84 60 84 Q20 84 20 98 Z" class="k milk t3"/><path d="M52 84 H68" class="k t5"/>
<path d="M134 98 L142 172 H198 L206 98" class="k t3"/>
<ellipse cx="170" cy="94" rx="46" ry="10" class="k milk t3"/><ellipse cx="170" cy="94" rx="24" ry="4.5" class="k"/>
{lbl(60,148,'Pee','tl','middle')}{lbl(170,148,'Poo','tl','middle')}
{lbl(60,64,'Lid','tb','middle')}{lead(60,68,60,80)}
{lbl(170,64,'Seat','tb','middle')}{lead(170,68,170,81)}
<path d="M258 172 Q292 112 326 172 Z" class="w wf"/>
<path d="M300 150 L322 118" class="w t3"/><ellipse cx="298" cy="152" rx="9" ry="5" transform="rotate(-50 298 152)" class="w wf"/>
{arrow(262,146,212,106)}
{lbl(336,24,'Cover material','tb','end')}{lbl(336,38,'half a cup (120 mL)','','end')}{lbl(336,52,'after each poo','','end')}{lead(282,58,284,142)}''')

svg('latrine', 200, 'Cat hole in side view: a hole 6 to 8 inches (15 to 20 cm) deep and 4 to 6 inches (10 to 15 cm) across, at least 200 feet (60 m) from water, with the soil you dug out beside it', f'''
<path d="M0 100 H20 Q28 124 50 124 Q72 124 80 100 H340 V200 H0 Z" class="gr m"/>
<path d="M22 108 Q50 100 78 108 Q72 122 50 122 Q28 122 22 108 Z" class="af"/><path d="M26 112 q6 -4 12 0 t12 0 t12 0" class="a t1"/>
<path d="M262 100 V138 H288 V100 Z" class="milk"/><path d="M262 100 V138 H288 V100" class="k t3"/>
<path d="M294 100 Q312 78 330 100 Z" class="w wf"/>
<path d="M232 62 L242 84" class="k t5"/><path d="M242 84 L252 82 L250 98 L240 100 Z" class="k kf"/>
{dim(80,48,262,48)}<line x1="80" y1="40" x2="80" y2="56" class="m"/><line x1="262" y1="40" x2="262" y2="56" class="m"/>
{lbl(171,22,'At least 200 feet (60 m) from water','tb','middle')}{lbl(171,36,'about 70 steps','tm','middle')}
{lbl(45,150,'Water,','tb','middle')}{lbl(45,164,'trails, camp','','middle')}
{dim(254,102,254,137)}{lbl(244,120,'6 to 8 inches','','end')}{lbl(244,134,'(15 to 20 cm) deep','','end')}
{dim(262,150,288,150)}{lbl(275,168,'4 to 6 inches','','middle')}{lbl(275,182,'(10 to 15 cm) across','','middle')}
{lbl(336,64,'Soil you','','end')}{lbl(336,76,'dug out','','end')}''')


svg('handwash-station', 226, 'Hand-washing station: a jug of treated water with an on/off spigot on a table, a bar of soap in a sock tied to its handle, a towel, and a catch bucket on the ground under the spigot', f'''
<line x1="6" y1="198" x2="180" y2="198" class="m"/>
<line x1="98" y1="122" x2="98" y2="198" class="k t3" data-part="leg"/><line x1="168" y1="122" x2="168" y2="198" class="k t3" data-part="leg"/>
<line x1="90" y1="122" x2="176" y2="122" class="k t5" data-part="table"/>
<rect x="100" y="52" width="46" height="70" rx="8" class="k"/><rect x="103" y="76" width="40" height="43" rx="6" class="af"/>
<rect x="114" y="42" width="18" height="10" rx="2" class="k kf"/>
<path d="M100 108 H49 V118" class="k t3"/><path d="M76 108 V98 M70 98 H82" class="k t3"/>
<line x1="49" y1="124" x2="49" y2="158" class="a t3 d" data-part="stream"/>
<path d="M146 62 H158 V84 H146" class="k t3"/>
<path d="M158 84 V88" class="k t1"/><path d="M151 88 H165 V104 Q165 112 158 112 Q151 112 151 104 Z" class="k milk"/><path d="M151 94 H165" class="m t1"/>
<path d="M162 118 H178 Q184 118 184 124 V150 Q181 155 178 150 Q175 155 172 150 V126 H162 Z" class="k milk"/>
<path d="M22 160 L27 198 H71 L76 160 Z" class="k" data-part="bucket"/><path d="M24 178 H74" class="a"/>
{lbl(190,40,'Jug with an on/off','')}{lbl(190,54,'spigot','')}{lead(188,46,138,60)}
{lbl(190,100,'Soap in a sock','')}{lead(188,96,166,96)}
{lbl(190,140,'Towel','')}{lead(188,136,185,136)}
{lbl(48,216,'Catch bucket','','middle')}''')

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
svg('shelter-debris', 195, 'Debris hut: ridgepole propped at waist height, ribs, debris at least 3 feet (1 metre) thick, thick leaf bed inside', f'''
<rect x="0" y="165" width="340" height="30" class="gr"/><line x1="0" y1="165" x2="340" y2="165" class="m"/>
<path d="M78 165 L80 156 Q170 148 272 160 L280 165 Z" class="gf g t1"/>
<line x1="70" y1="165" x2="70" y2="96" class="w t3"/><path d="M70 102 L60 86 M70 102 L80 86" class="w t3"/>
<line x1="52" y1="87" x2="312" y2="166" class="w t5"/>
{ribs}
<path d="M36 165 C28 104 50 60 92 62 C134 64 222 110 334 165" class="w wf t1"/>
<path d="M44 165 A15 15 0 0 1 72 165" class="k"/>
{lbl(150,36,'Ridgepole at waist height','tb')}{lead(170,40,148,112)}
{lbl(214,82,'Debris at least','')}{lbl(214,96,'3 ft (1 m) thick','')}{lead(212,94,190,104)}
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

# Tarp lean-to in a three-quarter view from the open side: the wind comes from the left onto the low, staked back edge.
svg('shelter-tarp', 222, 'Tarp lean-to: a rope from each corner of the high front edge tied to its tree about waist high, with a drip stick on each rope; the other long edge staked to the ground as the back, into the wind; the open side faces away from the wind', f'''
<path d="M50 156 L130 176 L270 148 L190 128" class="m t1"/>
<path d="M130 116 V176 M270 88 V148" class="m t1 d"/>
<path d="M130 116 L270 88 L190 128 L50 156 Z" class="g gf"/>
<line x1="130" y1="116" x2="270" y2="88" class="g t3" data-part="high-edge"/>
<line x1="50" y1="156" x2="190" y2="128" class="g t3" data-part="low-edge"/>
<path d="M50 156 l-5 10 M120 142 l-5 10 M190 128 l-5 10" class="w t3"/>
<line x1="90" y1="124" x2="130" y2="116" class="k t1"/><line x1="270" y1="88" x2="310" y2="80" class="k t1"/>
<line x1="124" y1="113" x2="124" y2="123" class="w t3"/><line x1="276" y1="83" x2="276" y2="93" class="w t3"/>
<line x1="90" y1="184" x2="90" y2="44" class="w t5"/><line x1="310" y1="140" x2="310" y2="20" class="w t5"/>
{arrow(4,122,40,131,'m','aM').replace('<line', '<line data-part="wind"', 1)}{arrow(4,142,32,149,'m','aM')}{lbl(4,112,'Wind','tm')}
{lbl(4,16,'Each rope tied to its','')}{lbl(4,30,'tree about waist high','')}{lead(100,35,110,118)}
{lbl(196,40,'Drip stick','')}{lead(232,44,274,82)}
<text x="150" y="104" transform="rotate(-11.3 150 104)" class="tb">High front edge</text>
{lbl(4,200,'Low, staked edge:','tb')}{lbl(4,214,'back into the wind','')}{lead(48,188,84,150)}
{lbl(336,186,'Open side faces','tb','end')}{lbl(336,200,'away from the wind','','end')}{lead(262,178,226,132)}''')

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

# Quinzhee cut across the middle: walls the depth of the sticks, a vent near the top, two raised beds with a trench between them
# down to the ground. Scale: 118 px = 5 ft, so the 24 px wall is just over 1 ft. No entrance is drawn: the steps give it no
# height, and the topic's rule (sleeping platform higher than the top of the entrance) cannot be shown from them (review C1, D64).
quin_sticks = ''.join(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="w t3"/>' for x1, y1, x2, y2 in
                      [(294.2, 150.3, 268.3, 160.8), (264.8, 109.7, 245.0, 129.5), (228.7, 86.3, 216.5, 111.5),
                       (111.3, 86.3, 123.5, 111.5), (75.2, 109.7, 95.0, 129.5), (45.8, 150.3, 71.7, 160.8)])
svg('quinzhee', 212, 'Quinzhee cut in half: a snow mound at least 5 feet (1.5 m) high, sticks pushed a foot (30 cm) deep so the walls stay at least 1 foot (30 cm) thick, a ventilation hole near the top, and raised beds with a trench down to the ground between them so cold air drains out', f'''
<rect x="0" y="196" width="340" height="16" class="gr"/><line x1="0" y1="196" x2="340" y2="196" class="m"/>
<path d="M40 196 A130 118 0 0 1 300 196 H276 A106 94 0 0 0 64 196 Z" class="snow" data-part="walls"/>
<path d="M64 196 L67.5 172 H158 V196 Z M182 196 V172 H272.5 L276 196 Z" class="snow" data-part="beds"/>
<rect x="182" y="76" width="8" height="29" class="milk"/><path d="M182 78.5 V103 M190 79 V103" class="k t1"/>
{quin_sticks}
{arrow(170,166,170,193,'a','aA')}
<line x1="24" y1="80" x2="24" y2="194" class="m" marker-start="url(#aM)" marker-end="url(#aM)"/><line x1="18" y1="78" x2="164" y2="78" class="m t1 d"/>
{lbl(30,30,'At least 5 feet','tb')}{lbl(30,44,'(1.5 m) high','')}
{lbl(336,20,'Sticks a foot (30 cm) deep:','tb','end')}{lbl(336,34,'walls at least 1 foot (30 cm) thick','','end')}{lead(296,38,256,118)}
{lbl(150,64,'Ventilation hole','','end')}{lead(152,62,180,82)}
{lbl(170,144,'Trench down to the ground','tb','middle')}{lbl(170,158,'so cold air drains out','','middle')}
{lbl(108,188,'Raised beds','tb','middle')}{lbl(232,188,'Raised beds','tb','middle')}''')

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

# ---------------- HEAT ----------------
def generator(x, y):
    """Portable generator, about 36 x 30, top-left corner at x, y."""
    return (f'<rect x="{x+6}" y="{y}" width="22" height="8" rx="2" class="k"/><rect x="{x}" y="{y+8}" width="36" height="20" rx="3" class="k milk"/>'
            f'<circle cx="{x+12}" cy="{y+18}" r="5" class="k"/><rect x="{x+22}" y="{y+13}" width="9" height="9" class="k t1"/>'
            f'<circle cx="{x+30}" cy="{y+31}" r="4" class="k"/><line x1="{x+4}" y1="{y+28}" x2="{x+4}" y2="{y+35}" class="k t3"/>')

svg('generator-placement', 206, 'Generator outside only, more than 20 feet (6 m) from any window, door or vent, with its exhaust pointed away from your home; never inside a home, garage, basement, crawlspace or shed, and never in an attached garage, even with the door open', f'''
<line x1="0" y1="180" x2="340" y2="180" class="m"/>
<path d="M2 118 L66 102" class="k t3"/><path d="M6 115 V180 M66 104 V180" class="k" data-part="garage"/>
<rect x="14" y="124" width="44" height="8" class="k kf"/><path d="M14 132 V180 M58 132 V180" class="k t1"/>
<g transform="translate(18 146) scale(0.8)">{generator(0, 0)}</g>
<path d="M14 142 L56 182 M56 142 L14 182" class="h" style="stroke-width:7" data-part="never"/>
<path d="M60 94 L108 52 L156 94" class="k t3"/><rect x="66" y="92" width="84" height="88" class="k" data-part="house"/>
<rect x="122" y="104" width="22" height="22" class="k"/><path d="M133 104 V126 M122 115 H144" class="k t1"/>
<rect x="80" y="136" width="20" height="44" class="k"/>
<line x1="150" y1="128" x2="264" y2="128" class="m" data-part="distance" marker-start="url(#aM)" marker-end="url(#aM)"/>
<line x1="264" y1="120" x2="264" y2="144" class="m t1"/>
<g data-part="generator">{generator(264, 145)}</g>
{arrow(302,166,334,166,'h','aH').replace('<line', '<line data-part="exhaust"', 1)}<path d="M308 156 q4 -4 8 0 t8 0 M314 176 q4 -4 8 0 t8 0" class="m t1"/>
{lbl(4,16,'Never inside a home, garage,','tb')}{lbl(4,30,'basement, crawlspace or shed','tb')}{lead(36,35,36,106)}
{lbl(207,102,'More than','tb','middle')}{lbl(207,116,'20 feet (6 m)','tb','middle')}
{lbl(207,146,'from any window,','','middle')}{lbl(207,160,'door or vent','','middle')}
{lbl(336,60,'Exhaust pointed','tb','end')}{lbl(336,74,'away from your home','','end')}{lead(320,78,320,148)}
{lbl(283,198,'Outside only','tb','middle')}''')

svg('heater-clearance', 210, 'Wood stove vented to the outside, with anything that can burn kept at least 3 feet (1 m) from it: an armchair on one side and curtains on the other', f'''
<line x1="0" y1="176" x2="340" y2="176" class="m"/><line x1="0" y1="44" x2="340" y2="44" class="m"/>
<rect x="164" y="10" width="12" height="104" class="k milk"/>
<rect x="138" y="114" width="64" height="54" rx="3" class="k"/><path d="M142 168 V176 M198 168 V176" class="k t3"/>
<rect x="150" y="124" width="40" height="36" rx="2" class="k t1"/>{flame(170,158,0.55)}
<path d="M8 118 Q8 104 20 104 H44 Q56 104 56 118 V138 H8 Z" class="k"/><path d="M4 134 H60 V160 H4 Z" class="k"/><path d="M8 160 V176 M56 160 V176" class="k t3"/>
<line x1="290" y1="56" x2="338" y2="56" class="k t3"/>
<path d="M294 58 Q290 110 296 172 H326 Q332 110 328 58" class="w wf"/><path d="M304 60 V170 M318 60 V170" class="w t1"/>
<line x1="60" y1="98" x2="136" y2="98" class="m" marker-start="url(#aM)" marker-end="url(#aM)"/>
<line x1="204" y1="98" x2="290" y2="98" class="m" marker-start="url(#aM)" marker-end="url(#aM)"/>
{lbl(98,74,'At least','tb','middle')}{lbl(98,88,'3 feet (1 m)','tb','middle')}
{lbl(247,74,'At least','tb','middle')}{lbl(247,88,'3 feet (1 m)','tb','middle')}
{lbl(184,26,'Vented to the outside','','start')}
{lbl(170,198,'Anything that can burn','','middle')}{lead(102,194,48,170)}{lead(238,194,296,170)}''')

def window(x1, y1, x2, y2):
    """A window in a plan-view wall: a gap with a thin double line."""
    if y1 == y2:
        return f'<rect x="{x1}" y="{y1-3}" width="{x2-x1}" height="6" class="milk"/><path d="M{x1} {y1-2} H{x2} M{x1} {y1+2} H{x2}" class="m t1"/>'
    return f'<rect x="{x1-3}" y="{y1}" width="6" height="{y2-y1}" class="milk"/><path d="M{x1-2} {y1} V{y2} M{x1+2} {y1} V{y2}" class="m t1"/>'

svg('warm-room', 214, 'House plan: one small warm room on the sheltered side of the house, with one window covered with a blanket at night and towels in the crack under its closed door; the other rooms are closed off and cold, with their heating ducts blocked off', f'''
<rect x="10" y="20" width="320" height="160" class="gr"/>
<rect x="10" y="100" width="130" height="80" class="hfl"/>
<rect x="10" y="20" width="320" height="160" class="k t3"/>
<path d="M170 20 V100 M10 100 H330 M140 100 V120 M140 156 V180" class="k t3"/>
<line x1="140" y1="120" x2="140" y2="156" class="w t3"/><path d="M140 156 A36 36 0 0 0 176 120" class="m t1 d"/><path d="M149 121 l6 4 l-6 4 l6 4 l-6 4 l6 4 l-6 4 l6 4 l-6 4" class="w t3" data-part="towel"/>
{window(40, 20, 80, 20)}{window(110, 20, 150, 20)}{window(220, 20, 260, 20)}{window(330, 40, 330, 70)}
{window(330, 122, 330, 152)}{window(270, 180, 310, 180)}{window(55, 180, 95, 180)}
<line x1="56" y1="174" x2="94" y2="174" class="w t5"/>
<rect x="286" y="78" width="18" height="10" class="k milk"/><path d="M286 78 L304 88 M304 78 L286 88" class="h t3"/>
{lbl(75,127,'Warm room','tl','middle')}
{lbl(75,146,'Blankets over the','','middle')}{lbl(75,160,'windows at night','','middle')}
{lbl(90,56,'Close off rooms','tb','middle')}{lbl(90,70,'you don’t need','','middle')}
{lbl(250,46,'Cold room','tm','middle')}{lbl(278,72,'Heating ducts','','end')}{lbl(278,86,'blocked off','','end')}
{lbl(184,134,'Towels in the cracks','')}{lbl(184,148,'under doors','')}{lbl(320,170,'Cold room','tm','end')}
<path d="M10 186 V190 H330 V186" class="m t1"/>
{lbl(170,206,'Sheltered side of the house','tb','middle')}''')

# ---------------- RADIATION ----------------
# Drawn from surv-fallout-where-to-shelter ("Best spot in a house", "Apartments and large buildings") and
# surv-fallout-coming-inside with p:radiation-decontamination. No amounts, no "safe" (radiation pack Task 7); the only
# numbers are the step badges, and the only arrow is the double arrow labelled "far" in panel 2 of fallout-coming-inside.
def person(cx, top, s=1.0, cls='k'):
    """Stick figure standing on y = top + 56*s."""
    hy, neck, hip, foot = top + 7 * s, top + 14 * s, top + 36 * s, top + 56 * s
    return (f'<circle cx="{cx}" cy="{hy:.1f}" r="{7*s:.1f}" class="{cls}"/>'
            f'<path d="M{cx} {neck:.1f} V{hip:.1f} M{cx-8*s:.1f} {foot:.1f} L{cx} {hip:.1f} L{cx+8*s:.1f} {foot:.1f}" class="{cls}"/>')

svg('fallout-shelter-spots', 418, 'Best spot in a house: the basement, go there first. Apartments and large buildings: the basement is best; otherwise go to the center of the building, as far from the roof and windows as you can, shown on a plan seen from above; stay away from areas near the roof, fire escapes and balconies', f'''
{lbl(170,18,'Best spot in a house','tl','middle')}
<rect x="60" y="94" width="220" height="44" class="gr"/>
<line x1="60" y1="94" x2="280" y2="94" class="m" data-part="ground-a"/>
<path d="M94 62 L170 30 L246 62" class="k t3"/>
<rect x="102" y="62" width="136" height="32" class="k t3" data-part="house-a"/>
{window(102, 70, 102, 86)}{window(238, 70, 238, 86)}
<rect x="102" y="94" width="136" height="38" class="milk"/>
<rect x="102" y="94" width="136" height="38" class="af" style="fill-opacity:.45" data-part="basement-a"/><path d="M102 94 V132 H238 V94" class="k t3"/>
<path d="M208 94 h8 v7 h8 v7 h8 v7" class="k t1"/>
{lbl(160,111,'Basement:','tb','middle')}{lbl(160,125,'go there first','tb','middle')}
<line x1="10" y1="152" x2="330" y2="152" class="m t1 d"/>
{lbl(170,174,'Apartments and large buildings','tl','middle')}
{lbl(236,194,'Basement is best','tb')}<path d="M300 199 V314 H186" class="m t1"/>
{lbl(150,212,'Stay away from areas near the roof,','','middle')}{lbl(150,226,'fire escapes and balconies','','middle')}
{lead(150,230,150,238)}{lead(98,230,94,250)}{lead(202,230,206,248)}
<rect x="0" y="300" width="340" height="36" class="gr"/>
<line x1="10" y1="343" x2="330" y2="343" class="m t1 d"/>
<rect x="105" y="240" width="90" height="60" class="k t3" data-part="bldg"/>
<path d="M101 240 H199" class="k t3"/><path d="M105 260 H195 M105 280 H195" class="k t1"/>
{''.join(window(105, y + 5, 105, y + 13) + window(195, y + 5, 195, y + 13) for y in (240, 260, 280))}
<g data-part="fire-escape"><path d="M87 258 H105 M87 278 H105" class="k"/><path d="M103 278 L89 258" class="k t1"/>
<path d="M87 250 V258 M87 270 V278" class="k t1"/></g>
<g data-part="balconies"><path d="M195 258 H213 M195 278 H213" class="k t3"/>
<path d="M213 250 V258 M213 270 V278 M201 250 H213 M201 270 H213" class="k t1"/></g>
<line x1="0" y1="300" x2="340" y2="300" class="m" data-part="ground-c"/>
<rect x="105" y="300" width="90" height="28" class="milk"/>
<rect x="105" y="300" width="90" height="28" class="af" style="fill-opacity:.45" data-part="basement-c"/><path d="M105 300 V328 H195 V300" class="k t3"/>
<rect x="20" y="350" width="100" height="60" class="milk"/>
<rect x="50" y="366" width="40" height="28" class="af" style="fill-opacity:.2" data-part="plan-center"/><path d="M50 366 H90 V394 H50 Z" class="a t1 d"/>
<rect x="20" y="350" width="100" height="60" class="k t3" data-part="plan"/>
<path d="M20 370 H38 M102 370 H120 M20 390 H38 M102 390 H120 M44 350 V360 M96 350 V360 M44 410 V400 M96 410 V400" class="k t1"/>
<g data-part="plan-windows">{window(26, 350, 38, 350)}{window(64, 350, 76, 350)}{window(102, 350, 114, 350)}{window(26, 410, 38, 410)}{window(64, 410, 76, 410)}{window(102, 410, 114, 410)}{window(20, 376, 20, 384)}{window(120, 376, 120, 384)}</g>
{lbl(136,366,'Otherwise go to the','tb')}{lbl(136,380,'center of the building,','')}{lbl(136,394,'as far from the roof and','')}{lbl(136,408,'windows as you can','')}
{lead(132,376,92,380)}''')

def shoe(x, y):
    """Side view of a shoe, heel at x, sole on y."""
    return f'<path d="M{x} {y} V{y-7} H{x+6} L{x+14} {y-3} Q{x+18} {y-2} {x+18} {y} Z" class="k t1"/>'

def cell(x0, y0, n, body, lines):
    """One numbered panel: badge, drawing in local coordinates (floor at y = 70), then label lines (text, class)."""
    labels = ''.join(lbl(x0 + 12, y0 + 92 + 14 * i, t, c) for i, (t, c) in enumerate(lines))
    return f'{badge(x0 + 12, y0 + 12, n)}<g transform="translate({x0} {y0 + 4})">{body}</g>{labels}'

C1 = f'''<line x1="24" y1="70" x2="164" y2="70" class="m"/>
<path d="M124 70 V6 H156 V70" class="k t3"/><path d="M124 8 L110 16 V76 L124 70" class="k milk"/>
{person(76, 14)}<path d="M76 34 L54 48 M76 34 L84 50" class="k"/>
<path d="M48 48 L45 50 L41 63 L45 64 L48 56 V68 H60 V56 L63 64 L67 63 L63 50 L60 48 Q54 51 48 48 Z" class="w wf"/>
{shoe(90, 70)}{shoe(106, 70)}'''
C2 = f'''<line x1="12" y1="70" x2="164" y2="70" class="m"/>
<g data-part="bag"><path d="M14 70 Q4 52 18 42 L23 37 H33 L38 42 Q52 52 42 70 Z" class="k gr" data-part="bag-shape"/>
<path d="M26 37 q-8 -9 -3 -12 q4 2 3 12 M30 37 q8 -9 3 -12 q-4 2 -3 12" class="k t1"/></g>
<g data-part="people-pets">{person(130, 14)}<path d="M130 34 L122 48 M130 34 L138 48" class="k"/>
<ellipse cx="152" cy="58" rx="9" ry="5" class="k"/><circle cx="163" cy="51" r="4" class="k"/><path d="M146 62 V70 M150 63 V70 M155 63 V70 M159 62 V70 M143 56 q-5 -3 -5 -9" class="k"/></g>
<line x1="58" y1="44" x2="114" y2="44" class="m" marker-start="url(#aM)" marker-end="url(#aM)"/>'''
C3 = f'''<line x1="24" y1="70" x2="164" y2="70" class="m"/>
<path d="M124 70 V0 H108 V4" class="k t3"/><path d="M98 4 H118 L114 10 H102 Z" class="k kf"/>
<path d="M94 14 L88 38 M100 14 L97 28 M116 14 L119 28 M122 14 L128 38 M92 42 L88 58 M124 42 L128 58" class="a t1 d"/>
{person(108, 14)}<path d="M108 34 L98 24 M108 34 L118 24" class="k"/>
<rect x="34" y="58" width="22" height="12" rx="4" class="k milk"/>'''
C4 = f'''<circle cx="64" cy="38" r="24" class="k milk"/>
<path d="M40 32 q-8 0 -8 8 q0 8 8 8 M88 32 q8 0 8 8 q0 8 -8 8" class="k"/>
<circle cx="56" cy="34" r="2" class="kf"/><circle cx="72" cy="34" r="2" class="kf"/><path d="M64 38 V46 H60 M58 54 H70" class="k t1"/>
<path d="M8 72 Q14 58 30 56 L42 40" class="k t3"/><rect x="40" y="26" width="18" height="13" rx="2" transform="rotate(-12 49 32)" class="w wf"/>
<path d="M124 70 Q116 58 126 50 L129 46 H137 L140 50 Q150 58 142 70 Z" class="k gr"/><path d="M131 46 q-5 -6 -2 -8 q3 1 2 8 M135 46 q5 -6 2 -8 q-3 1 -2 8" class="k t1"/>
<line x1="108" y1="70" x2="164" y2="70" class="m"/>'''
C5 = f'''<line x1="24" y1="70" x2="164" y2="70" class="m"/>
<rect x="30" y="26" width="52" height="44" class="k"/><path d="M30 40 H82 M30 54 H82" class="k t1"/>
<circle cx="56" cy="33" r="2" class="kf"/><circle cx="56" cy="47" r="2" class="kf"/><circle cx="56" cy="61" r="2" class="kf"/>
<path d="M114 18 L100 26 L106 38 L112 34 V64 H144 V34 L150 38 L156 26 L142 18 Q128 26 114 18 Z" class="k milk"/>'''
C6 = f'''<path d="M10 30 H130 Q150 28 158 36 Q162 44 152 52 Q140 58 130 56 H10" class="skin"/>
<rect x="58" y="24" width="40" height="38" rx="4" class="k milk"/><path d="M58 34 L98 30 M58 44 L98 40 M58 54 L98 50" class="k t1"/>'''

svg('fallout-coming-inside', 532, 'Save a life first. Then: 1 take off the outer layer of clothes and shoes slowly and carefully, before coming in or just inside the door, away from others; 2 bag them and put the bag far from people and pets; 3 wash gently with soap and water, or wipe off, no conditioner, no scrubbing; 4 blow the nose and wipe the eyes and ears, and bag every wipe, cloth and towel you used; 5 put on clean clothes from a closet, drawer or other covered place; 6 care for wounds once the skin around a wound is clean. Then help others and pets, and clean yourself again afterwards', f'''
{lbl(170,18,'Save a life first. Then:','tl','middle')}
<line x1="170" y1="30" x2="170" y2="486" class="m t1 d"/><line x1="4" y1="204" x2="336" y2="204" class="m t1 d"/>
<line x1="4" y1="354" x2="336" y2="354" class="m t1 d"/><line x1="4" y1="490" x2="336" y2="490" class="m t1 d"/>
{cell(0, 30, '1', C1, [('Take off the outer layer','tb'), ('of clothes and shoes','tb'), ('slowly and carefully','tb'), ('Do it before coming in,',''), ('or just inside the door,',''), ('away from others','')])}
{cell(172, 30, '2', C2, [('Bag them','tb'), ('Put the bag far from',''), ('people and pets','')])}
{lbl(258,66,'far','','middle')}
{cell(0, 208, '3', C3, [('Wash gently with soap','tb'), ('and water, or wipe off','tb'), ('No conditioner,',''), ('no scrubbing','')])}
{cell(172, 208, '4', C4, [('Blow the nose and wipe','tb'), ('the eyes and ears','tb'), ('Bag every wipe, cloth',''), ('and towel you used','')])}
{cell(0, 358, '5', C5, [('Put on clean clothes','tb'), ('from a closet, drawer',''), ('or other covered place','')])}
{cell(172, 358, '6', C6, [('Care for wounds','tb'), ('once the skin around a',''), ('wound is clean','')])}
{lbl(170,508,'Then help others and pets, and','tb','middle')}{lbl(170,522,'clean yourself again afterwards','','middle')}''')

# ---------------- FOOD ----------------
# Food pack Task 7, drawn from the checked text only. food-fridge-freezer: surv-food-power-out, "How long it stays cold" (the
# table and Do first 1, 5); its only numbers are the three hold times, each beside "keeps food cold for" and "with the door
# shut". food-cans-to-discard: surv-food-still-good, "Cans and jars" (CDC's four signs and the botulism warning); no number,
# no can drawn without a sign, no flood rule. Neither says "safe". Defects are drawn in blaze, liquid in blue.
def chest(x, y, k, rows):
    """Chest freezer seen from the front with its front wall cut away: body x..x+92, y..y+56, lid shut on top. rows: list of
    (top, bottom, [x widths]) blocks of food packed side by side."""
    food = ''.join(f'<rect x="{bx}" y="{top}" width="{w}" height="{bot - top}" rx="2" class="k wf t1"/>'
                   for top, bot, xs in rows for bx, w in xs)
    return (f'<rect x="{x}" y="{y}" width="92" height="56" class="k milk t3" data-part="body-{k}"/>'
            f'<g data-part="food-{k}">{food}</g>'
            f'<rect x="{x-4}" y="{y-10}" width="100" height="10" rx="2" class="k milk t3" data-part="lid-{k}"/>'
            f'<rect x="{x+38}" y="{y-6}" width="16" height="3" rx="1" class="kf"/>'
            f'<path d="M{x+6} {y+56} v5 M{x+86} {y+56} v5" class="k t3"/>')

def hold(y, who, hours):
    return (f'{lbl(130, y, who, "tb")}{lbl(130, y + 18, "keeps food cold for")}{lbl(130, y + 38, hours, "tl")}'
            f'{lbl(130, y + 56, "with the door shut")}')

FULL = [(221, 235, [(25, 26), (51, 30), (81, 26)]), (206, 221, [(25, 34), (59, 22), (81, 26)]),
        (191, 206, [(25, 22), (47, 32), (79, 28)])]
HALF = [(321, 335, [(25, 30), (55, 24), (79, 28)]), (308, 321, [(25, 24), (49, 32), (81, 26)])]

svg('food-fridge-freezer', 418, 'Keep the fridge and freezer doors shut. With the door shut, a fridge keeps food cold for about 4 hours, a full freezer about 48 hours and a half-full freezer about 24 hours. Before you eat, cook or refreeze anything, check it in Is it still good?', f'''
{lbl(170,20,'Keep the fridge and freezer doors shut','tl','middle')}
<line x1="4" y1="32" x2="336" y2="32" class="m t1 d"/>
<rect x="36" y="42" width="60" height="100" rx="5" class="k milk t3" data-part="fridge"/>
<rect x="40" y="46" width="52" height="92" rx="3" class="m t1"/>
<rect x="82" y="58" width="5" height="34" rx="2" class="kf" data-part="fridge-handle"/>
<path d="M42 142 v5 M90 142 v5" class="k t3"/>
{hold(62, 'Fridge', 'about 4 hours')}
<line x1="4" y1="154" x2="336" y2="154" class="m t1 d"/>
{chest(20, 182, 'full', FULL)}
{hold(178, 'Full freezer', 'about 48 hours')}
<line x1="4" y1="254" x2="336" y2="254" class="m t1 d"/>
{chest(20, 282, 'half', HALF)}
{hold(278, 'Half-full freezer', 'about 24 hours')}
<line x1="4" y1="354" x2="336" y2="354" class="m t1 d"/>
{lbl(170,374,'Before you eat, cook or refreeze anything,','tb','middle')}{lbl(170,390,'check it in','','middle')}
{lbl(170,408,'Is it still good?','tl','middle')}''')

def can_body(cx, y, h, w=44, cls='k milk'):
    """Side view of a can: top rim ellipse at y, straight sides, rounded bottom at y + h."""
    r = w / 2
    return (f'<path d="M{cx-r} {y} V{y+h} A{r} 6 0 0 0 {cx+r} {y+h} V{y} Z" class="{cls}"/>'
            f'<path d="M{cx-r} {y+h*0.35:.0f} A{r} 6 0 0 0 {cx+r} {y+h*0.35:.0f} M{cx-r} {y+h*0.7:.0f} A{r} 6 0 0 0 {cx+r} {y+h*0.7:.0f}" class="m t1"/>')

def jar(cx, y, h=50, w=40):
    """Glass jar, mouth at y, body to y + h."""
    r = w / 2
    return (f'<path d="M{cx-r+6} {y} V{y+6} Q{cx-r} {y+8} {cx-r} {y+14} V{y+h-6} Q{cx-r} {y+h} {cx-r+6} {y+h} H{cx+r-6} '
            f'Q{cx+r} {y+h} {cx+r} {y+h-6} V{y+14} Q{cx+r} {y+8} {cx+r-6} {y+6} V{y} Z" class="k milk"/>')

S1 = f'''<g data-part="sign-1">
{can_body(85, 76, 38)}
<path d="M63 76 Q85 52 107 76 Q85 82 63 76 Z" class="h t3 hfl"/>
<path d="M63 114 Q85 140 107 114" class="h t3"/>
<path d="M107 104 q4 8 0 12 q-4 -4 0 -12 Z M112 118 q4 8 0 12 q-4 -4 0 -12 Z" class="afs"/>
<ellipse cx="118" cy="136" rx="12" ry="3" class="afs"/></g>'''
S2 = f'''<g data-part="sign-2">
{jar(222, 72, 56)}<rect x="206" y="62" width="32" height="10" rx="2" class="k gr"/>
<path d="M214 86 L224 96 L216 104 L228 116 L222 124" class="h t3"/>
<path d="M272 72 V88 L280 94 L276 99 L283 104 L277 109 L272 114 V124 A22 6 0 0 0 316 124 V114 L310 108 L306 103 L312 98 L307 93 L316 88 V72 Z" class="k milk"/>
<ellipse cx="294" cy="72" rx="22" ry="6" class="k milk"/>
<path d="M272 84 A22 6 0 0 0 316 84 M272 117 A22 6 0 0 0 316 117" class="m t1"/>
<path d="M285 96 l5 4 M296 94 l-3 6 M302 103 l-6 3 M288 106 l4 -2" class="h t3"/></g>'''
S3 = f'''<g data-part="sign-3">
{can_body(85, 240, 40)}
<ellipse cx="85" cy="240" rx="22" ry="5" class="k"/>
<ellipse cx="54" cy="226" rx="20" ry="5" transform="rotate(-35 54 226)" class="k milk"/>
<path d="M78 236 L66 208 M86 234 L86 204 M94 236 L108 208" class="a t3"/>
<circle cx="62" cy="202" r="4" class="a t1"/><circle cx="74" cy="198" r="3" class="a t1"/><circle cx="88" cy="196" r="5" class="a t1"/>
<circle cx="102" cy="200" r="3.5" class="a t1"/><circle cx="114" cy="204" r="4" class="a t1"/>
<path d="M118 216 q4 8 0 12 q-4 -4 0 -12 Z M56 214 q4 8 0 12 q-4 -4 0 -12 Z" class="afs"/></g>'''
S4 = f'''<g data-part="sign-4">
{jar(240, 226, 58)}
<path d="M224 240 H256 V278 H224 Z" class="wf"/>
<path d="M223 242 q-2 -8 5 -9 q1 -8 9 -6 q4 -7 11 -2 q8 -3 9 5 q6 2 3 12 Z" class="g gf t3"/>
<path d="M229 236 h0.1 M236 231 h0.1 M244 233 h0.1 M251 237 h0.1 M240 238 h0.1" class="g t5"/>
<path d="M228 252 q6 -4 10 2 q4 6 -2 9 q-8 2 -8 -11 Z M244 262 q6 -2 8 4 q0 6 -6 5 q-5 -2 -2 -9 Z" class="g gf"/></g>'''

svg('food-cans-to-discard', 508, 'Cans and jars: throw it out if the container is leaking, bulging or swollen; looks damaged, cracked or abnormal; spurts liquid or foam when opened; or the food is discolored, moldy or smells bad. You cannot see, smell or taste the toxin that causes botulism, and even a small taste of food that has it can be deadly. It can be in cans that look normal and in food that smells and tastes normal. How to get rid of a suspect can or jar without touching what is inside: Food poisoning and botulism.', f'''
{lbl(170,20,'Any of these signs:','tl','middle')}{lbl(170,40,'Throw it out','tl','middle')}
<line x1="4" y1="50" x2="336" y2="50" class="m t1 d"/>
<line x1="170" y1="54" x2="170" y2="330" class="m t1 d"/><line x1="4" y1="192" x2="336" y2="192" class="m t1 d"/>
{S1}{lbl(85,158,'Leaking, bulging','tb','middle')}{lbl(85,172,'or swollen','tb','middle')}
{S2}{lbl(255,158,'Looks damaged,','tb','middle')}{lbl(255,172,'cracked or abnormal','tb','middle')}
{S3}{lbl(85,304,'Spurts liquid or foam','tb','middle')}{lbl(85,318,'when opened','tb','middle')}
{S4}{lbl(255,304,'Food is discolored,','tb','middle')}{lbl(255,318,'moldy or smells bad','tb','middle')}
<line x1="4" y1="334" x2="336" y2="334" class="m t1 d"/>
{lbl(170,354,'You cannot see, smell or taste','tb','middle')}{lbl(170,368,'the toxin that causes botulism,','tb','middle')}
{lbl(170,382,'and even a small taste of food that has it','tb','middle')}{lbl(170,396,'can be deadly.','tb','middle')}
{lbl(170,418,'It can be in cans that look normal','tb','middle')}{lbl(170,432,'and in food that smells and tastes normal.','tb','middle')}
<line x1="4" y1="446" x2="336" y2="446" class="m t1 d"/>
{lbl(170,466,'How to get rid of a suspect can or jar','','middle')}{lbl(170,480,'without touching what is inside:','','middle')}
{lbl(170,500,'Food poisoning and botulism','tl','middle')}''')

# ---------------- FIRE ----------------
svg('fire-sizes', 142, 'Fire materials: dry, fine tinder; kindling from pencil lead to thumb thick; fuel forearm thick and up', f'''
<path d="M30 58 c5 -22 34 -24 42 -6 c8 16 -12 30 -26 22 c-14 -8 -4 -26 12 -22 c12 4 10 16 0 18 M40 48 c8 -6 20 -4 22 6 M36 66 c10 8 26 6 30 -6" class="w t1"/>
{lbl(55,100,'Tinder','tb','middle')}{lbl(55,116,'dry, fine','tm','middle')}{lbl(55,130,'material','tm','middle')}
<line x1="124" y1="40" x2="196" y2="46" class="w t1"/><line x1="126" y1="54" x2="198" y2="58" class="w"/><line x1="124" y1="70" x2="196" y2="72" class="w t3"/>
{lbl(160,100,'Kindling','tb','middle')}{lbl(160,116,'pencil lead','tm','middle')}{lbl(160,130,'to thumb thick','tm','middle')}
<line x1="244" y1="44" x2="316" y2="40" style="stroke-width:10" class="w"/><line x1="242" y1="68" x2="318" y2="70" style="stroke-width:15" class="w"/>
{lbl(280,100,'Fuel','tb','middle')}{lbl(280,116,'forearm thick','tm','middle')}{lbl(280,130,'and up','tm','middle')}''')

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

# Ferro rod, Army method: rod tip at the tinder, striker square to the rod and driven down it toward the tip.
svg('fire-ferro', 190, 'Ferro rod: the rod held with its tip at the tinder; the striker at a right angle to the rod, driven down the rod with firm, even pressure so the sparks land in the tinder', f'''
<line x1="0" y1="150" x2="340" y2="150" class="m"/>
<ellipse cx="234" cy="138" rx="38" ry="12" class="w wf" data-part="tinder"/>
<path d="M214 136 c6 -8 18 -10 30 -2 M220 144 c10 4 22 2 28 -6" class="w t1"/>
<line x1="96" y1="30" x2="240" y2="130" class="st t5" data-part="rod"/>
<line x1="96" y1="30" x2="74" y2="15" style="stroke-width:11" class="w"/>
<line x1="153.6" y1="70" x2="173" y2="42.1" class="k t5" data-part="striker"/>
<path d="M157.6 64.3 L163.4 68.2 L159.4 74" class="k t1"/>
<line x1="166.1" y1="51.9" x2="215.4" y2="86.1" class="h t3" marker-end="url(#aH)" data-part="push"/>
<path d="M236 134 l-8 5 M242 135 l3 8 M246 131 l10 3 M234 128 l-10 0" class="h t1"/>
<circle cx="226" cy="128" r="1.6" class="hf"/><circle cx="250" cy="126" r="1.6" class="hf"/><circle cx="220" cy="134" r="1.6" class="hf"/>
{lbl(8,40,'Ferro rod','tb')}
{lbl(176,18,'Striker at a right angle','tb')}{lbl(176,32,'to the rod','')}
{lbl(336,60,'Drive it down the rod','tb','end')}{lbl(336,74,'firm, even pressure','','end')}
{lbl(8,128,'Rod tip at the tinder','')}{lead(128,126,224,132)}
{lbl(234,174,'Sparks land in the tinder','tb','middle')}''')

svg('fire-platform', 150, 'A base of green logs in two crosswise layers keeps a fire off deep snow', f'''
<rect x="0" y="112" width="340" height="38" class="snow"/>
{lbl(12,140,'Deep snow','tm')}
{''.join(f'<circle cx="{x}" cy="106" r="6" class="w wfs"/>' for x in range(112, 236, 12))}
<line x1="104" y1="94" x2="240" y2="94" style="stroke-width:7" class="w"/>
{flame(170,90,1.0)}{flame(172,90,0.55,'h hf')}
{lbl(336,44,'Green logs only,','tb','end')}{lbl(336,58,'two layers,','','end')}{lbl(336,72,'crosswise','','end')}{lead(296,78,240,100)}''')

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
svg('trap-snare', 190, 'Simple snare hung over a game trail: a loop big enough to slip over the animal’s head, with twigs funneling the animal in', f'''
<rect x="0" y="165" width="340" height="25" class="gr"/><line x1="0" y1="165" x2="340" y2="165" class="m"/>
<line x1="90" y1="165" x2="90" y2="34" class="w t3"/><line x1="250" y1="165" x2="250" y2="34" class="w t3"/>
<path d="M90 42 l-8 -10 M250 42 l8 -10" class="w t3"/>
<line x1="80" y1="40" x2="262" y2="40" class="w t3"/>
<line x1="132" y1="165" x2="138" y2="100" class="w"/><line x1="122" y1="165" x2="132" y2="112" class="w t1"/>
<line x1="208" y1="165" x2="202" y2="100" class="w"/><line x1="218" y1="165" x2="208" y2="112" class="w t1"/>
<line x1="170" y1="40" x2="170" y2="97" class="k t1"/>
<circle cx="170" cy="125" r="28" class="k"/>
{lbl(170,24,'Wire tied to a solid support','','middle')}
{lbl(336,70,'Loop big','tb','end')}{lbl(336,84,'enough to','','end')}{lbl(336,98,'slip over the','','end')}{lbl(336,112,'animal’s head','','end')}{lead(290,118,198,126)}
{lbl(8,90,'Twigs funnel','')}{lbl(8,104,'it into','')}{lbl(8,118,'the loop','')}{lead(62,116,128,130)}''')

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



# ---------------- SIGNALS ----------------


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

trk = rope_svg([([(40,22,0),(120,48,0),(196,74,0),(212,86,1),(205,100,0),(196,92,-1),(194,104,0),(214,140,0),(246,168,0),(262,160,-1),(256,140,0),(222,100,0),(204,86,-1),(194,70,0),(214,62,2),(240,96,1),(282,150,0),(300,170,0)], 'rp')])

# ---------------- NEW SECTIONS ----------------
svg('lightning', 150, 'Count from flash to thunder: every 5 seconds is about 1 mile. If you can hear thunder you can be struck. Wait 30 minutes after the last thunder.', f'''
<path d="M20 58 C8 58 6 40 20 36 C20 20 42 14 52 26 C60 10 90 12 94 30 C110 28 116 50 102 58 Z" class="gr m"/>
<polygon points="60,58 46,96 60,96 50,134 82,86 66,86 78,58" class="hf"/>
<path d="M112 70 q10 20 0 40 M124 62 q14 28 0 56 M136 54 q18 36 0 72" class="m t1"/>
{lbl(160,34,'Count flash to thunder:','tb')}{lbl(160,50,'5 seconds ≈ 1 mile')}
{lbl(160,76,'Hear thunder? You’re','tb')}{lbl(160,92,'close enough to be struck.')}
{lbl(160,118,'Wait 30 minutes after','tb')}{lbl(160,134,'the last thunder.')}''')


svg('river', 200, 'River crossing: face upstream, pole planted upstream, shuffle across at about 45 degrees downstream, away from strainers', f'''
<rect x="0" y="40" width="340" height="128" class="af"/>
<line x1="0" y1="40" x2="340" y2="40" class="m"/><line x1="0" y1="168" x2="340" y2="168" class="m"/>
{arrow(14,70,54,70,'a','aA')}{arrow(14,140,54,140,'a','aA')}{lbl(14,62,'Current','tm')}
<path d="M44 36 L176 168" class="k d" marker-end="url(#aK)"/>
<circle cx="110" cy="102" r="8" class="kf"/>
<line x1="102" y1="100" x2="74" y2="92" class="w t3"/>
<path d="M272 58 L330 122 M290 70 l-10 12 M306 88 l12 -8 M318 104 l-12 10" class="w t3"/>
{lbl(150,112,'Face upstream,','tb')}{lbl(150,126,'pole upstream','')}
{lbl(330,148,'Strainers and rapids:','tb','end')}{lbl(330,162,'never cross just above them','','end')}
{lbl(84,24,'About 45° downstream','tb')}''')

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

# ---------------- REVISIONS (override earlier drafts) ----------------
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

svg('signal-mirror', 170, 'Signal mirror: sight the aircraft through a V of two fingers and aim the reflected light through the V', f'''
{sun(30,28,10)}
<line x1="40" y1="40" x2="62" y2="106" class="h d t1"/>
<polygon points="52,110 70,104 74,118 56,124" class="k af"/>
<line x1="64" y1="113" x2="290" y2="57" class="h" marker-end="url(#aH)"/>
<path d="M193 132 L182 78 M193 132 L206 80" class="skin-s"/>
<circle cx="194" cy="138" r="9" class="skin"/>
<path d="M286 58 L322 49 M300 40 L308 68" class="k t3"/>
{lbl(10,152,'Mirror','tb')}
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

# ---------------- EMERGENCY (positioning only: no wounds, no blood, no cross-sections) ----------------
def arm_limb():
    """Straight arm from the shoulder side (left) to the hand (right); the left edge is left open."""
    return ('<path d="M12 52 L120 52 C150 54 190 62 262 66 L262 96 C190 102 150 102 120 98 L12 98" class="skin"/>'
            '<ellipse cx="288" cy="81" rx="28" ry="15" class="skin"/>')

svg('tq-placement', 160, 'Arm seen from the side: the tourniquet band 2 to 3 inches above the wound, toward the heart, and not over the elbow', f'''
{arm_limb()}
<circle cx="126" cy="76" r="27" class="m d"/>
<rect x="190" y="56" width="18" height="50" rx="4" class="k kf"/>
<path d="M234 75 l12 12 m0 -12 l-12 12" class="h t3"/>
{arrow(118,26,14,26,'m','aM')}{lbl(14,16,'Toward the heart','tm')}
{lbl(199,40,'Tourniquet','tb','middle')}{lead(199,44,199,54)}
{lbl(272,40,'Wound','tb','middle')}{lead(266,46,248,72)}
<path d="M208 116 v8 M240 116 v8 M208 120 H240" class="k"/>
{lbl(224,140,'2 to 3 inches','tb','middle')}{lbl(224,154,'above the wound','','middle')}
{lbl(14,128,'Not over the elbow','tb')}{lbl(14,142,'or knee','tb')}{lead(70,114,106,94)}''')
svg('cpr-hands-adult', 256, 'Adult CPR hand position: heel of one hand on the lower half of the breastbone in the centre of the chest, other hand on top, arms straight with shoulders over the hands, pushing straight down', f'''
<path d="M46 40 Q80 54 114 40 L134 52 Q146 60 146 76 V170 H14 V76 Q14 60 26 52 Z" class="k"/>
<line x1="80" y1="60" x2="80" y2="132" class="m t1 d"/>
<rect x="60" y="100" width="40" height="30" rx="8" class="h t3 hfl"/>
<rect x="56" y="80" width="48" height="34" rx="8" class="k milk"/>
<path d="M66 80 v-8 M76 80 v-10 M86 80 v-10 M96 80 v-8" class="k"/>
{lbl(80,192,'Centre of the chest','tb','middle')}{lbl(80,206,'Heel of one hand on','','middle')}{lbl(80,220,'the lower half of the','','middle')}{lbl(80,234,'breastbone, other hand','','middle')}{lbl(80,248,'on top','','middle')}
<line x1="168" y1="170" x2="336" y2="170" class="m t1"/>
<circle cx="186" cy="156" r="13" class="skin"/>
<rect x="202" y="146" width="70" height="24" rx="8" class="skin"/>
<rect x="272" y="152" width="64" height="18" rx="8" class="skin"/>
<rect x="214" y="134" width="36" height="12" rx="4" class="h t3 hfl"/>
<line x1="224" y1="134" x2="224" y2="76" class="k t5"/><line x1="240" y1="134" x2="240" y2="76" class="k t5"/>
<circle cx="232" cy="46" r="14" class="k"/>
<path d="M232 66 L262 104" class="m t3 d"/>
{arrow(232,78,232,130,'h','aH')}
{lbl(237,164,'chest','tm','middle')}
{lbl(250,192,'Arms straight,','tb','middle')}{lbl(250,206,'shoulders over your','','middle')}{lbl(250,220,'hands, push straight','','middle')}{lbl(250,234,'down','','middle')}''')

def infant_chest(cx):
    return (f'<path d="M{cx-40} 40 Q{cx} 52 {cx+40} 40 L{cx+56} 52 Q{cx+64} 60 {cx+64} 76 V150 H{cx-64} V76 Q{cx-64} 60 {cx-56} 52 Z" class="k"/>'
            f'<line x1="{cx-50}" y1="68" x2="{cx+50}" y2="68" class="m t1 d"/>'
            f'<circle cx="{cx-26}" cy="68" r="2.5" class="kf"/><circle cx="{cx+26}" cy="68" r="2.5" class="kf"/>'
            f'<line x1="{cx}" y1="56" x2="{cx}" y2="124" class="m t1"/>')

svg('cpr-infant', 245, 'Infant CPR hand positions on the centre of the chest, lower half of the breastbone just below the nipple line: two thumbs side by side with the fingers wrapped around the chest, or the heel of one hand', f'''
{infant_chest(84)}
<ellipse cx="76" cy="96" rx="8" ry="15" class="h t3 hfl"/><ellipse cx="92" cy="96" rx="8" ry="15" class="h t3 hfl"/>
<path d="M66 108 C46 120 30 118 14 104 M102 108 C122 120 138 118 154 104" class="k t3"/>
{lbl(14,22,'Nipple line','tm')}{lead(48,26,58,64)}
{lbl(84,172,'Two thumbs side by side','tb','middle')}{lbl(84,186,'just below the nipple line.','','middle')}{lbl(84,200,'Fingers wrap around the','','middle')}{lbl(84,214,'chest toward the back','','middle')}
<line x1="170" y1="30" x2="170" y2="222" class="m t1 d"/>
{infant_chest(256)}
<rect x="236" y="80" width="40" height="30" rx="9" class="h t3 hfl"/>
{lbl(256,172,'Or the heel of one hand','tb','middle')}{lbl(256,186,'in the same spot','','middle')}''')

svg('back-blows', 250, 'Back blows: the person bent forward at the waist so the upper body is about level with the ground, one of your arms across their chest, the heel of your other hand striking between the shoulder blades, you standing to the side and slightly behind', f'''
<line x1="20" y1="196" x2="330" y2="196" class="m t1"/>
<circle cx="76" cy="112" r="13" class="k"/>
<line x1="90" y1="104" x2="172" y2="114" class="k t5"/>
<path d="M172 114 L186 194 L170 194" class="k t3"/>
<path d="M104 106 L100 156" class="k t3"/>
<ellipse cx="128" cy="105" rx="22" ry="8" class="h d"/>
<circle cx="164" cy="42" r="14" class="m t3 d"/>
<path d="M164 58 L168 134 L164 194 L180 194" class="m t3 d"/>
<path d="M166 72 L134 94" class="m t3 d"/>
<path d="M168 80 L134 122 L106 120" class="m t3 d"/>
{arrow(118,50,122,92,'h','aH')}
{lbl(10,22,'Heel of your other hand,','tb')}{lbl(10,36,'between the shoulder','tb')}{lbl(10,50,'blades','tb')}
{lbl(330,100,'Stand to the','tb','end')}{lbl(330,114,'side and slightly','tb','end')}{lbl(330,128,'behind','tb','end')}{lead(268,104,171,68)}
{lbl(10,216,'One arm across the chest. Bend them','')}{lbl(10,230,'forward at the waist, upper body about','')}{lbl(10,244,'level with the ground','')}''')

svg('abdominal-thrusts', 210, 'Abdominal thrusts: stand behind the person with your arms around their waist, one fist just above the belly button with the thumb side against the belly and your other hand over it, pulling sharply in and up', f'''
<line x1="20" y1="196" x2="330" y2="196" class="m t1"/>
<circle cx="150" cy="40" r="14" class="k"/>
<path d="M150 56 L156 124 L152 194 L132 194" class="k t5"/>
<circle cx="196" cy="34" r="14" class="m t3 d"/>
<path d="M194 50 L202 126 L206 194 L224 194" class="m t3 d"/>
<path d="M190 74 L162 96 L132 104" class="m t3 d"/>
<circle cx="143" cy="104" r="9" class="h hfl t3"/>
<circle cx="144" cy="104" r="13" class="h t3"/>
<circle cx="148" cy="126" r="3" class="kf"/>
{arrow(88,162,126,134,'h','aH')}
{lbl(10,22,'Stand behind them,','tb')}{lbl(10,36,'arms around the waist','tb')}
{lbl(10,62,'Fist just above','tb')}{lbl(10,76,'the belly button,','tb')}{lbl(10,90,'other hand over it','tb')}{lead(116,90,132,100)}
{lbl(10,158,'Pull sharply','tb')}{lbl(10,172,'in and up','tb')}
{lbl(10,126,'Belly button','')}{lead(74,122,144,126)}''')

svg('splint-forearm', 190, 'Forearm splint: a padded rigid splint along the forearm that reaches past the joint above and the joint below, tied above and below the injury and not over it', f'''
<path d="M34 54 H250 C268 54 276 58 296 60 V100 C276 102 268 104 250 104 H34 Q24 104 24 94 V64 Q24 54 34 54 Z" class="skin"/>
<rect x="14" y="112" width="296" height="10" rx="4" class="k"/>
<rect x="18" y="102" width="288" height="10" rx="3" class="w wf"/>
<path d="M26 107 H300" class="w t1 d"/>
<circle cx="40" cy="79" r="20" class="m d"/><circle cx="262" cy="79" r="18" class="m d"/>
<circle cx="150" cy="79" r="16" class="h d"/>
<rect x="98" y="48" width="12" height="78" rx="4" class="k wf t3"/><rect x="196" y="48" width="12" height="78" rx="4" class="k wf t3"/>
{lbl(40,36,'Joint above','tb','middle')}{lbl(262,36,'Joint below','tb','middle')}
{lbl(150,20,'Injury','tb','middle')}{lead(150,24,150,60)}
{lbl(104,146,'Tie above','tb','middle')}{lbl(202,146,'and below','tb','middle')}
{lbl(170,164,'not over the injury','tb','middle')}
{lbl(14,184,'Padded rigid splint reaches past both joints','')}{lbl(326,146,'Padding','tb','end')}{lead(300,138,284,110)}''')

svg('pressure-dressing', 236, 'Pressure dressing: keep pressing hard with both hands on the dressing until the bleeding stops, then wrap a firm bandage over the dressing', f'''
<path d="M14 90 H326 V122 H14 Z" class="skin"/>
<rect x="136" y="82" width="68" height="8" rx="3" class="k milk"/>
<rect x="144" y="64" width="52" height="18" rx="6" class="h t3 hfl"/>
<line x1="156" y1="64" x2="156" y2="14" class="k t5"/><line x1="184" y1="64" x2="184" y2="14" class="k t5"/>
{arrow(232,24,232,76,'h','aH')}
{lbl(14,22,'Keep pressing','tb')}{lbl(14,36,'until the bleeding','tb')}{lbl(14,50,'stops','tb')}
{lbl(14,78,'Dressing','')}{lead(66,76,134,85)}
<line x1="20" y1="132" x2="320" y2="132" class="m t1 d"/>
{lbl(14,156,'Then wrap a firm bandage','tb')}{lbl(14,170,'over the dressing','tb')}
<path d="M14 188 H326 V220 H14 Z" class="skin"/>
<path d="M118 184 L152 184 L140 224 L106 224 Z M146 184 L180 184 L168 224 L134 224 Z M174 184 L208 184 L196 224 L162 224 Z M202 184 L236 184 L224 224 L190 224 Z" class="k wf"/>''')

# ---------------- LAND (v7.7): deer, side view, facing left ----------------
# One outline for the three deer figures, drawn only from each topic's checked text. Coordinates are the deer's own; each
# figure places it with a translate. The far legs and far ear are drawn first, in the muted line, so the near ones read in front.
DEER_BODY = ('M24 52 C26 46 36 38 46 32 L52 28 C56 18 62 12 72 8 C72 16 68 26 62 34 '
             'C70 46 84 66 102 78 C140 72 200 72 236 76 C254 80 262 92 260 108 '
             'C258 128 252 146 250 160 L256 178 L250 218 L240 220 L244 182 '
             'C240 166 236 150 226 138 C220 132 212 128 204 128 C176 132 140 138 116 138 '
             'L116 178 L116 218 L106 220 L106 180 C104 160 100 146 92 136 '
             'C84 128 80 116 80 106 C78 92 68 78 56 68 C46 62 32 60 24 52 Z')
DEER_EAR2 = 'M50 30 C50 20 52 12 58 4 C62 12 60 22 56 32'
DEER_FAR = ('M142 136 L138 178 L142 218 L134 220 L130 180 L132 136 Z '
            'M208 130 C220 142 228 160 232 182 L228 218 L236 220 L242 180 C240 166 236 150 230 138 Z')
DEER_TAIL = 'M259 92 C268 94 272 104 268 116 C263 112 260 106 259 100'
def deer(dx, dy, extra=''):
    return (f'<g transform="translate({dx} {dy})" data-part="deer"><path d="{DEER_FAR}" class="m t1 milk"/>'
            f'<path d="{DEER_EAR2}" class="k t1 milk"/><path d="{DEER_BODY}" class="k milk"/>'
            f'<path d="{DEER_TAIL}" class="k t1 milk"/><circle cx="40" cy="42" r="2.2" class="kf"/>{extra}</g>')

# Shot placement (surv-land-big-game): broadside; the near front leg's back edge (x 116) followed up into the body; the chest
# from its bottom (y 138) to the top of the back (y 76) ticked at both ends and at one third (no two-thirds tick: it read as a second
# aim mark); the aim spot one third of the way up, in the heart and lungs.
_vx, _vb, _vt = 116, 138, 76
_vl = [_vb - (_vb - _vt) * i / 3 for i in range(4)]
_ax, _ay = _vx + 36, round(_vl[1] + 60, 1)
svg('land-deer-vitals', 330, 'Deer seen broadside (side-on), facing left, with the heart and lungs shaded in the chest. Aim just behind the shoulder: follow the back edge of the front leg nearest you up into the body, and aim about one third of the way up from the bottom of the chest. Pick one small spot there, smaller than a pie plate.', f'''
{deer(36, 60, '<ellipse cx="128" cy="113" rx="25" ry="20" class="h hfl" data-part="vital"/>'
      f'<line x1="{_vx}" y1="{_vt}" x2="{_vx}" y2="{_vb + 80}" class="k t1 d" data-part="leg-line"/>'
      + ''.join(f'<line x1="{_vx - 12}" y1="{y:.1f}" x2="{_vx + 12}" y2="{y:.1f}" class="k" data-part="third"/>' for y in (_vl[0], _vl[1], _vl[3])))}
<circle cx="{_ax}" cy="{_ay}" r="7" class="k t3" data-part="aim"/><circle cx="{_ax}" cy="{_ay}" r="2" class="kf"/>
{lbl(6,18,'Broadside (side-on)','tb')}
{lbl(334,18,'Aim just behind the shoulder','tb','end')}{lbl(334,32,'Pick one small spot there,','','end')}{lbl(334,46,'smaller than a pie plate','','end')}
{lead(_ax + 20, 52, _ax + 4, _ay - 6)}
{lbl(200,168,'Heart and lungs','tb')}{lead(198,164,189,164)}
{lbl(6,236,'About one third','')}{lbl(6,250,'of the way up from','')}{lbl(6,264,'the bottom of the chest','')}{lead(110,240,_ax - 6,_ay + 12)}
{lbl(170,308,'Follow the back edge','')}{lbl(170,322,'of the front leg nearest you','')}{lead(168,304,_vx + 38,230)}''')

# Butchering (surv-land-butchering, "The cuts and what each is good for"): where each cut comes from, in the table's words.
# Seams in the coyote line; the tenderloin is inside, so it is dashed. The shank is a label and leader to the hind leg below its
# knee, with no boundary drawn: the text names where it starts (the knee joint) but not where it ends.
svg('land-deer-cuts', 340, 'Deer seen from the side, facing left, showing where each cut comes from: neck, between the shoulders and the head; shoulder; backstrap (loin), along the spine over the ribs; ribs; flank; tenderloin, inside, along the underside of the spine, near the pelvis; hind leg: sirloin, top round, bottom round, eye of round; shank, the lower leg, below the knee', f'''
{deer(36, 60, '<path d="M100 77 C94 90 88 102 82 116" class="w" data-part="seam-neck"/>'
      '<path d="M122 74 C128 96 126 120 117 138" class="w" data-part="seam-shoulder"/>'
      '<path d="M122 90 C160 86 190 86 211 88" class="w" data-part="seam-backstrap"/>'
      '<path d="M164 87 C168 104 168 120 164 134" class="w" data-part="seam-ribs"/>'
      '<path d="M212 74 C208 96 204 114 206 130" class="w" data-part="seam-hind-leg"/>'
      '<path d="M172 96 C182 92 200 92 210 96 C200 100 182 100 172 96 Z" class="k d" data-part="tenderloin"/>')}
{lbl(179,178,'Ribs','','middle')}{lbl(203,184,'Flank','')}
{lbl(336,16,'Hind leg','tb','end')}{lbl(336,30,'Sirloin','','end')}{lbl(336,44,'Top round, bottom round,','','end')}{lbl(336,58,'eye of round','','end')}{lead(316,64,268,164)}
{lbl(150,104,'Backstrap (loin)','tb')}{lead(196,108,202,142)}
{lbl(6,150,'Neck','tb')}{lead(40,146,120,148)}
{lbl(6,196,'Shoulder','tb')}{lead(62,192,144,178)}
{lbl(336,224,'Shank','tb','end')}{lead(298,220,279,214)}
{lbl(140,302,'Tenderloin','tb')}{lbl(140,316,'inside, along the underside','')}{lbl(140,330,'of the spine, near the pelvis','')}{lead(234,292,240,160)}''')
