# This Python file uses the following encoding: utf-8
from drawingDimensioning.command import *
import subprocess

class ExportToDxfCommand:
    def Activated(self):
        V = getDrawingPageGUIVars()
        dialog = QtGui.QFileDialog(
            QtGui.QApplication.activeWindow(),
            "Enter the dxf file name"
            )
        dialog.setAcceptMode(QtGui.QFileDialog.AcceptSave)
        dialog.setNameFilter("DXF files (*.dxf)")
        lineEdit = [c for c in dialog.children() if isinstance(c, QtGui.QLineEdit) ][0]
        lineEdit.setText(FreeCAD.ActiveDocument.Label + '.dxf')
        if dialog.exec_():
            dxf_fn = dialog.selectedFiles()[0]
            debugPrint(3,'saving to %s' % dxf_fn)
            export_via_dxfwrite( dxf_fn, V)
            #export_via_pstoedit( dxf_fn, V)

    def GetResources(self): 
        #menuText = 'shortcut command for exporting active drawing page to dxf (requires inkscape and pstoedit)'
        menuText = 'alternative dxf export command which uses the dxfwrite python library'
        return {
            'Pixmap' : ':/dd/icons/exportToDxf.svg',
            'MenuText': menuText, 
            } 

FreeCADGui.addCommand('dd_exportToDxf', ExportToDxfCommand())


def shellCmd(cmd, callDirectory=None):
    debugPrint(3,'$' + cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=callDirectory)
    stdout, stderr = p.communicate()
    if stdout <> '':
        debugPrint(3,'stdout:%s' % stdout )
    if p.returncode <> 0:
        raise RuntimeError, '$ %s \n STDERR:%s' % (cmd, stderr)
    return stdout


def export_via_pstoedit( dxf_fn, V):
    eps_fn = dxf_fn[:-4] + '.eps'
    if os.path.exists(eps_fn):
        raise RuntimeError,"eps file (%s) exists, aborting operation" % eps_fn
    V.page.PageResult
    shellCmd('inkscape -f %s -E %s' % (V.page.PageResult, eps_fn)) #circle maintained after this step
    try:
        shellCmd("pstoedit -dt -f 'dxf:-polyaslines -mm' -flat 0.01 %s %s" % (eps_fn, dxf_fn) )
        # man pstoedit
        # -dt: Draw text - Text is drawn as polygons
        # -f "format[:options]" target output format recognized by pstoedit.
        # -flat [flatness factor] If the output format does not support curves in the way PostScript does or if the -nc option is specified, all curves are approximated by lines. Using the -flat option  one  can  control  this approximation. This parameter is directly converted to a PostScript setflat command. Higher numbers, e.g. 10 give rougher, lower numbers, e.g. 0.1 finer approximations. #I the default is 1
        QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Success", "%s successfully created" % dxf_fn )
    except RuntimeError, msg:
        QtGui.QMessageBox.critical( QtGui.QApplication.activeWindow(), "pstoedit failed.", "%s\n\n suggestion: relaunch FreeCAD from BASH and try again." % msg )
        #only works if FreeCAD is launched from bash shell?
        #work around for this?
        shellCmd('rm %s' % eps_fn)


def export_via_dxfwrite(  dxf_fn, V):
    from drawingDimensioning.XMLlib import SvgXMLTreeNode
    from drawingDimensioning.svgLib import SvgTextParser, SvgPath, SvgPolygon
    from drawingDimensioning.circleLib import fitCircle_to_path, findCircularArcCentrePoint, pointsAlongCircularArc
    from numpy import arctan2
    from dxfwrite import DXFEngine as dxf
    drawing = dxf.drawing( dxf_fn)
    
    pageSvg = open(V.page.PageResult).read()
    XML_tree =  SvgXMLTreeNode( pageSvg,0)
    defaultHeight = 0
    defaultFont = 'Verdana'
    defaultAnchor = 'left'
    def yT(y): #y transform
        return 210-y
    warningsShown = []
    SelectViewObjectPoint_loc = None
    for element in XML_tree.getAllElements():
        clr_text = None        
        if element.parms.has_key('fill'):
            clr_text =  element.parms['fill']
        elif element.parms.has_key('style'):
            for part in element.parms['style'].split(';'):
                if part.startswith('stroke:rgb('):
                    clr_text = part[ len('stroke:'):]
                elif part.startswith('font-size'):
                    defaultHeight = part[len('font-size:')]
                elif part.startswith('font-family'):
                    defaultFont = part[len('font-family:'):]
                elif part.startswith('text-anchor'):
                    defaultAnchor = part[len('text-anchor:'):]
        if clr_text == None or clr_text =='none' or not clr_text.startswith('rgb(') :
            color_code = 0
        else:
            #FreeCAD.Console.PrintMessage( "color text: %s\n" % clr_text )
            r,g,b = [ int(v.strip()) for v in clr_text[ len('rgb('): clr_text.find(')')].split(',') ]
            color_code = colorLookup(r,g,b)[0]
        if element.tag == 'circle':
            x, y = element.applyTransforms( float( element.parms['cx'] ), float( element.parms['cy'] ) )
            r =  float( element.parms['r'] )* element.scaling2()
            drawing.add( dxf.circle( r, (x,yT(y)), color=color_code) )
        elif element.tag == 'line':
            x1, y1 = element.applyTransforms( float( element.parms['x1'] ), float( element.parms['y1'] ) )
            x2, y2 = element.applyTransforms( float( element.parms['x2'] ), float( element.parms['y2'] ) )
            drawing.add( dxf.line( (x1, yT(y1)), (x2, yT(y2)), color=color_code ) )
        elif element.tag == 'text' and element.parms.has_key('x'):
            x,y = element.applyTransforms( float( element.parms['x'] ), float( element.parms['y'] ) )
            t = SvgTextParser(element.XML[element.pStart: element.pEnd ] )
            try:
                drawing.add(dxf.text( t.text, insert=(x, yT(y)), height=t.height()*0.8, rotation=t.rotation, layer='TEXTLAYER', color=color_code) )
            except ValueError, msg:
                temp = t.text.replace('<tspan>','')
                temp = temp.replace('</tspan>','')
                t.text = temp
                t.font_size = defaultHeight
                t.font_family = defaultFont          
                if defaultAnchor == 'middle':
                    shift = t.width()/2.0   
                    x,y = element.applyTransforms( float( element.parms['x'] )-shift, float( element.parms['y'] ) )
                drawing.add(dxf.text( temp, insert=(x, yT(y)), height=t.height()*0.8, rotation=t.rotation, layer='TEXTLAYER', color=color_code) )
                #FreeCAD.Console.PrintWarning('dxf_export: unable to convert text element "%s": %s, ignoring...\n' % (element.XML[element.pStart: element.pEnd ], str(msg) ) )
        elif element.tag == 'path': 
            #FreeCAD.Console.PrintMessage(element.parms['d']+'\n')
            path = SvgPath( element )
            for line in path.lines:
                drawing.add( dxf.line( (line.x1, yT(line.y1)), (line.x2,yT(line.y2)), color=color_code) ) 
            for arc in path.arcs:
                if arc.circular:
                    for r, center, angle1, angle2 in arc.dxfwrite_arc_parms( yT ):
                        drawing.add( dxf.arc( r, center, angle1, angle2 , color=color_code) )
                else:
                    for x1,y1,x2,y2 in arc.approximate_via_lines( 12 ):
                        drawing.add( dxf.line( (x1, yT(y1)), (x2, yT(y2)), color=color_code) )
            for bezierCurve in path.bezierCurves:
                x, y, r, r_error = bezierCurve.fitCircle()
                if r_error < 10**-4:
                    drawing.add( dxf.arc( *bezierCurve.dxfwrite_arc_parms(x, y, r), color=color_code ) )
                else:
                    X,Y = bezierCurve.points_along_curve()
                    for i in range(len(X) -1):
                        drawing.add( dxf.line( (X[i], yT(Y[i])), (X[i+1],yT(Y[i+1])), color=color_code ) )
        elif element.tag == 'polygon':
            p = SvgPolygon( element )
            for line in p.lines:
                drawing.add( dxf.line( (line.x1, yT(line.y1)), (line.x2,yT(line.y2)), color=color_code) ) 
        elif element.tag == 'rect':
            x, y = element.applyTransforms( float( element.parms['x'] ), float( element.parms['y'] ) )
            width =  float( element.parms['width'] )* element.scaling2()
            height =  float( element.parms['height'] )* element.scaling2()
            drawing.add(dxf.rectangle((x, yT(y)), width, -height, color = color_code) )
        elif not element.tag in warningsShown:
            FreeCAD.Console.PrintWarning('dxf_export: Warning export of %s elements not supported, ignoring...\n' % element.tag )
            warningsShown.append(element.tag)
    drawing.save()
    FreeCAD.Console.PrintMessage("dxf_export: %s successfully created\n" % dxf_fn)



#http://sub-atomic.com/~moses/acadcolors.html
color_table_text = '''0	0	0	0	0	0	0
FF	0	0	1	255	0	0
FF	FF	0	2	255	255	0
0	FF	0	3	0	255	0
0	FF	FF	4	0	255	255
0	0	FF	5	0	0	255
FF	0	FF	6	255	0	255
FF	FF	FF	7	255	255	255
41	41	41	8	65	65	65
80	80	80	9	128	128	128
FF	0	0	10	255	0	0
FF	AA	AA	11	255	170	170
BD	0	0	12	189	0	0
BD	7E	7E	13	189	126	126
81	0	0	14	129	0	0
81	56	56	15	129	86	86
68	0	0	16	104	0	0
68	45	45	17	104	69	69
4F	0	0	18	79	0	0
4F	35	35	19	79	53	53
FF	3F	0	20	255	63	0
FF	BF	AA	21	255	191	170
BD	2E	0	22	189	46	0
BD	8D	7E	23	189	141	126
81	1F	0	24	129	31	0
81	60	56	25	129	96	86
68	19	0	26	104	25	0
68	4E	45	27	104	78	69
4F	13	0	28	79	19	0
4F	3B	35	29	79	59	53
FF	7F	0	30	255	127	0
FF	D4	AA	31	255	212	170
BD	5E	0	32	189	94	0
BD	9D	7E	33	189	157	126
81	40	0	34	129	64	0
81	6B	56	35	129	107	86
68	34	0	36	104	52	0
68	56	45	37	104	86	69
4F	27	0	38	79	39	0
4F	42	35	39	79	66	53
FF	BF	0	40	255	191	0
FF	EA	AA	41	255	234	170
BD	8D	0	42	189	141	0
BD	AD	7E	43	189	173	126
81	60	0	44	129	96	0
81	76	56	45	129	118	86
68	4E	0	46	104	78	0
68	5F	45	47	104	95	69
4F	3B	0	48	79	59	0
4F	49	35	49	79	73	53
FF	FF	0	50	255	255	0
FF	FF	AA	51	255	255	170
BD	BD	0	52	189	189	0
BD	BD	7E	53	189	189	126
81	81	0	54	129	129	0
81	81	56	55	129	129	86
68	68	0	56	104	104	0
68	68	45	57	104	104	69
4F	4F	0	58	79	79	0
4F	4F	35	59	79	79	53
BF	FF	0	60	191	255	0
EA	FF	AA	61	234	255	170
8D	BD	0	62	141	189	0
AD	BD	7E	63	173	189	126
60	81	0	64	96	129	0
76	81	56	65	118	129	86
4E	68	0	66	78	104	0
5F	68	45	67	95	104	69
3B	4F	0	68	59	79	0
49	4F	35	69	73	79	53
7F	FF	0	70	127	255	0
D4	FF	AA	71	212	255	170
5E	BD	0	72	94	189	0
9D	BD	7E	73	157	189	126
40	81	0	74	64	129	0
6B	81	56	75	107	129	86
34	68	0	76	52	104	0
56	68	45	77	86	104	69
27	4F	0	78	39	79	0
42	4F	35	79	66	79	53
3F	FF	0	80	63	255	0
BF	FF	AA	81	191	255	170
2E	BD	0	82	46	189	0
8D	BD	7E	83	141	189	126
1F	81	0	84	31	129	0
60	81	56	85	96	129	86
19	68	0	86	25	104	0
4E	68	45	87	78	104	69
13	4F	0	88	19	79	0
3B	4F	35	89	59	79	53
0	FF	0	90	0	255	0
AA	FF	AA	91	170	255	170
0	BD	0	92	0	189	0
7E	BD	7E	93	126	189	126
0	81	0	94	0	129	0
56	81	56	95	86	129	86
0	68	0	96	0	104	0
45	68	45	97	69	104	69
0	4F	0	98	0	79	0
35	4F	35	99	53	79	53
0	FF	3F	100	0	255	63
AA	FF	BF	101	170	255	191
0	BD	2E	102	0	189	46
7E	BD	8D	103	126	189	141
0	81	1F	104	0	129	31
56	81	60	105	86	129	96
0	68	19	106	0	104	25
45	68	4E	107	69	104	78
0	4F	13	108	0	79	19
35	4F	3B	109	53	79	59
0	FF	7F	110	0	255	127
AA	FF	D4	111	170	255	212
0	BD	5E	112	0	189	94
7E	BD	9D	113	126	189	157
0	81	40	114	0	129	64
56	81	6B	115	86	129	107
0	68	34	116	0	104	52
45	68	56	117	69	104	86
0	4F	27	118	0	79	39
35	4F	42	119	53	79	66
0	FF	BF	120	0	255	191
AA	FF	EA	121	170	255	234
0	BD	8D	122	0	189	141
7E	BD	AD	123	126	189	173
0	81	60	124	0	129	96
56	81	76	125	86	129	118
0	68	4E	126	0	104	78
45	68	5F	127	69	104	95
0	4F	3B	128	0	79	59
35	4F	49	129	53	79	73
0	FF	FF	130	0	255	255
AA	FF	FF	131	170	255	255
0	BD	BD	132	0	189	189
7E	BD	BD	133	126	189	189
0	81	81	134	0	129	129
56	81	81	135	86	129	129
0	68	68	136	0	104	104
45	68	68	137	69	104	104
0	4F	4F	138	0	79	79
35	4F	4F	139	53	79	79
0	BF	FF	140	0	191	255
AA	EA	FF	141	170	234	255
0	8D	BD	142	0	141	189
7E	AD	BD	143	126	173	189
0	60	81	144	0	96	129
56	76	81	145	86	118	129
0	4E	68	146	0	78	104
45	5F	68	147	69	95	104
0	3B	4F	148	0	59	79
35	49	4F	149	53	73	79
0	7F	FF	150	0	127	255
AA	D4	FF	151	170	212	255
0	5E	BD	152	0	94	189
7E	9D	BD	153	126	157	189
0	40	81	154	0	64	129
56	6B	81	155	86	107	129
0	34	68	156	0	52	104
45	56	68	157	69	86	104
0	27	4F	158	0	39	79
35	42	4F	159	53	66	79
0	3F	FF	160	0	63	255
AA	BF	FF	161	170	191	255
0	2E	BD	162	0	46	189
7E	8D	BD	163	126	141	189
0	1F	81	164	0	31	129
56	60	81	165	86	96	129
0	19	68	166	0	25	104
45	4E	68	167	69	78	104
0	13	4F	168	0	19	79
35	3B	4F	169	53	59	79
0	0	FF	170	0	0	255
AA	AA	FF	171	170	170	255
0	0	BD	172	0	0	189
7E	7E	BD	173	126	126	189
0	0	81	174	0	0	129
56	56	81	175	86	86	129
0	0	68	176	0	0	104
45	45	68	177	69	69	104
0	0	4F	178	0	0	79
35	35	4F	179	53	53	79
3F	0	FF	180	63	0	255
BF	AA	FF	181	191	170	255
2E	0	BD	182	46	0	189
8D	7E	BD	183	141	126	189
1F	0	81	184	31	0	129
60	56	81	185	96	86	129
19	0	68	186	25	0	104
4E	45	68	187	78	69	104
13	0	4F	188	19	0	79
3B	35	4F	189	59	53	79
7F	0	FF	190	127	0	255
D4	AA	FF	191	212	170	255
5E	0	BD	192	94	0	189
9D	7E	BD	193	157	126	189
40	0	81	194	64	0	129
6B	56	81	195	107	86	129
34	0	68	196	52	0	104
56	45	68	197	86	69	104
27	0	4F	198	39	0	79
42	35	4F	199	66	53	79
BF	0	FF	200	191	0	255
EA	AA	FF	201	234	170	255
8D	0	BD	202	141	0	189
AD	7E	BD	203	173	126	189
60	0	81	204	96	0	129
76	56	81	205	118	86	129
4E	0	68	206	78	0	104
5F	45	68	207	95	69	104
3B	0	4F	208	59	0	79
49	35	4F	209	73	53	79
FF	0	FF	210	255	0	255
FF	AA	FF	211	255	170	255
BD	0	BD	212	189	0	189
BD	7E	BD	213	189	126	189
81	0	81	214	129	0	129
81	56	81	215	129	86	129
68	0	68	216	104	0	104
68	45	68	217	104	69	104
4F	0	4F	218	79	0	79
4F	35	4F	219	79	53	79
FF	0	BF	220	255	0	191
FF	AA	EA	221	255	170	234
BD	0	8D	222	189	0	141
BD	7E	AD	223	189	126	173
81	0	60	224	129	0	96
81	56	76	225	129	86	118
68	0	4E	226	104	0	78
68	45	5F	227	104	69	95
4F	0	3B	228	79	0	59
4F	35	49	229	79	53	73
FF	0	7F	230	255	0	127
FF	AA	D4	231	255	170	212
BD	0	5E	232	189	0	94
BD	7E	9D	233	189	126	157
81	0	40	234	129	0	64
81	56	6B	235	129	86	107
68	0	34	236	104	0	52
68	45	56	237	104	69	86
4F	0	27	238	79	0	39
4F	35	42	239	79	53	66
FF	0	3F	240	255	0	63
FF	AA	BF	241	255	170	191
BD	0	2E	242	189	0	46
BD	7E	8D	243	189	126	141
81	0	1F	244	129	0	31
81	56	60	245	129	86	96
68	0	19	246	104	0	25
68	45	4E	247	104	69	78
4F	0	13	248	79	0	19
4F	35	3B	249	79	53	59
33	33	33	250	51	51	51
50	50	50	251	80	80	80
69	69	69	252	105	105	105
82	82	82	253	130	130	130
BE	BE	BE	254	190	190	190
FF	FF	FF	255	255	255	255'''

dxf_colours = numpy.zeros([ 256, 3 ])

for line in color_table_text.split('\n'):
    parts = line.split()
    ind = int(parts[3])
    r,g,b = map(int, parts[4:])
    dxf_colours[ind] = r,g,b

def colorLookup(r,g,b):
    clr = numpy.array([r,g,b])
    errors = [ numpy.linalg.norm( clr - row) for row in dxf_colours ]
    min_ind = errors.index( min(errors) )
    return min_ind, dxf_colours[min_ind]
