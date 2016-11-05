//Maya ASCII 2016 scene
//Name: closestPoints2016.ma
//Codeset: 932
requires maya "2016";
requires -nodeType "exprespy" "exprespy" "2.0.0.20161029";
requires "exprespy" "2.0.0.20161024";
currentUnit -l centimeter -a degree -t ntsc;
createNode transform -n "src";
	setAttr ".t" -type "double3" 0.27127445757474922 1.7888933585030466 3.8683356068961023 ;
createNode locator -n "srcShape" -p "src";
	setAttr -k off ".v";
createNode transform -n "mesh";
	setAttr ".t" -type "double3" 5.632067430872163 -1.1985887354147602 -2.8597605393152614 ;
	setAttr ".r" -type "double3" -15.768918003454544 -23.105601081460691 28.244591082041961 ;
	setAttr ".s" -type "double3" 0.73166762953415854 1 1 ;
createNode mesh -n "meshShape" -p "mesh";
	setAttr -k off ".v";
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".pv" -type "double2" 0.50000005960464478 0.5 ;
	setAttr ".uvst[0].uvsn" -type "string" "map1";
	setAttr ".cuvs" -type "string" "map1";
	setAttr ".dcc" -type "string" "Ambient+Diffuse";
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
createNode transform -n "onMesh";
	setAttr ".dla" yes;
createNode locator -n "onMeshShape" -p "onMesh";
	setAttr -k off ".v";
createNode transform -n "surface";
	setAttr ".t" -type "double3" -5.4800856624630727 1.111062842063574 0.098486855272546414 ;
	setAttr ".r" -type "double3" -7.3750399348455815 23.41051763395145 13.298676106216449 ;
	setAttr ".s" -type "double3" 0.79695528159764628 0.81056336020299391 1 ;
createNode nurbsSurface -n "surfaceShape" -p "surface";
	setAttr -k off ".v";
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".tw" yes;
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
	setAttr ".dvu" 0;
	setAttr ".dvv" 0;
	setAttr ".cpr" 4;
	setAttr ".cps" 4;
	setAttr ".nufa" 4.5;
	setAttr ".nvfa" 4.5;
createNode transform -n "onSurface";
	setAttr ".dla" yes;
createNode locator -n "onSurfaceShape" -p "onSurface";
	setAttr -k off ".v";
createNode transform -n "curve";
	setAttr ".t" -type "double3" -1.215021588510325 -0.90088029598887243 9.3668461749941017 ;
	setAttr ".r" -type "double3" 2.5369908407080506 -26.497832752808954 -0.097162655198908113 ;
createNode nurbsCurve -n "curveShape" -p "curve";
	setAttr -k off ".v";
	setAttr ".cc" -type "nurbsCurve" 
		3 6 0 no 3
		11 0 0 0 1 2 3 4 5 6 6 6
		9
		-8.1186685962373346 0.6079313575699512 0.86929937005748403
		-6.0363385952841746 -0.77928080208396278 2.9966510343121895
		-1.1317933993422549 -0.6828367935315951 2.0892345987829755
		-2.3474229217735134 -0.6828367935315951 -1.6878999887712958
		-1.2156295224312579 2.5162002573386397 -3.0380812377572779
		1.8668596237337214 2.5162002573386397 -2.6039278368889711
		3.646888567293777 -0.8627455520771603 0.6522226696233302
		6.5123010130246044 -0.8627455520771603 0.60880732953649908
		8.1186685962373346 0.6079313575699512 -2.6039278368889711
		;
createNode transform -n "onCurve";
createNode locator -n "onCurveShape" -p "onCurve";
	setAttr -k off ".v";
createNode exprespy -n "exprCurve";
	setAttr ".cd" -type "string" "if not COUNT:\n    from maya.api.OpenMaya import MPoint, MFnNurbsCurve\n    kWorld = api.MSpace.kWorld\n\n    def compute(curve, src):\n        fn = MFnNurbsCurve(curve)\n        pos, u = fn.closestPoint(src, space=kWorld)\n        pos *= IN[0]\n        OUT[0] = pos\n\ncompute(\n    IN[1],\n    MPoint(IN[2]) * IN[3])";
	setAttr -s 4 ".i";
createNode exprespy -n "exprSurf";
	setAttr ".cd" -type "string" "# Using the tranformGeometry node because an error occurs\n# when specifies kWorld to MFnNurbsSurface.closestPoint.\n# \nif not COUNT:\n    from maya.api.OpenMaya import (\n        MPoint, MMatrix, MEulerRotation, MFnNurbsSurface)\n\n    def compute(surface, srcPos):\n        fn = MFnNurbsSurface(surface)\n        #trn, u, v = fn.closestPoint(srcPos, space=api.MSpace.kWorld)\n        pos, u, v = fn.closestPoint(srcPos)\n        pos *= IN[0]\n        OUT[0] = pos\n\n        vy = fn.normal(u, v)\n        vx, vz = fn.tangents(u, v)\n        vx.normalize()\n        vz = vx ^ vy\n        m = MMatrix([\n            vx.x, vx.y, vx.z, 0.,\n            vy.x, vy.y, vy.z, 0.,\n            vz.x, vz.y, vz.z, 0.,\n            0., 0., 0., 1.\n        ])\n        m *= IN[0]\n        rot = MEulerRotation([0., 0., 0.], IN[1])\n        rot.setValue(m)\n        OUT[1] = rot\n\ncompute(\n    IN[2],\n    MPoint(IN[3]) * IN[4])";
	setAttr -s 5 ".i";
	setAttr -s 2 ".o";
createNode transformGeometry -n "transformGeometry2";
createNode makeNurbTorus -n "makeNurbTorus1";
	setAttr ".ax" -type "double3" 0 1 0 ;
	setAttr ".r" 3;
	setAttr ".nsp" 4;
	setAttr ".hr" 0.33333333333333331;
createNode exprespy -n "exprMesh";
	setAttr ".cd" -type "string" (
		"# Using the tranformGeometry node because an error occurs\n# when gives a matrix to MMeshIntersector.create method.\n# \nif not COUNT:\n    from maya.api.OpenMaya import (\n        MPoint, MVector, MMatrix, MEulerRotation,\n        MMeshIntersector, MFnMesh)\n\n    def compute(mesh, srcPos):\n        mi = MMeshIntersector()\n        #mi.create(mesh, api.MFnGeometryData(mesh).matrix)  # why error happed?\n        mi.create(mesh)\n        pom = mi.getClosestPoint(srcPos)\n\n        pos = MPoint(pom.point)\n        pos *= IN[0]\n        OUT[0] = pos\n\n        fn = MFnMesh(mesh)\n        f = pom.face\n        tri = fn.getPolygonTriangleVertices(f, pom.triangle)\n        v0, v1, v2 = [fn.getFaceVertexTangent(f, v) for v in tri]\n        bu, bv = pom.barycentricCoords\n        vx = (v2 + (v0 - v2) * bu + (v1 - v2) * bv).normalize()\n        vy = MVector(pom.normal).normalize()\n        vz = vx ^ vy\n        m = MMatrix([\n            vx.x, vx.y, vx.z, 0.,\n            vy.x, vy.y, vy.z, 0.,\n            vz.x, vz.y, vz.z, 0.,\n            0., 0., 0., 1.\n"
		+ "        ])\n        m *= IN[0]\n        rot = MEulerRotation([0., 0., 0.], IN[1])\n        rot.setValue(m)\n        OUT[1] = rot\n\ncompute(\n    IN[2],\n    MPoint(IN[3]) * IN[4])");
	setAttr -s 5 ".i";
	setAttr -s 2 ".o";
createNode transformGeometry -n "transformGeometry1";
createNode polySoftEdge -n "polySoftEdge1";
	setAttr ".uopa" yes;
	setAttr ".ics" -type "componentList" 1 "e[*]";
	setAttr ".ix" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1;
	setAttr ".a" 59.999999999999993;
createNode polyTorus -n "polyTorus1";
	setAttr ".r" 3;
	setAttr ".sr" 1;
	setAttr ".sh" 8;
select -ne :time1;
	setAttr ".o" 1;
	setAttr ".unw" 1;
select -ne :renderPartition;
	setAttr -s 2 ".st";
select -ne :renderGlobalsList1;
select -ne :defaultShaderList1;
	setAttr -s 4 ".s";
select -ne :postProcessList1;
	setAttr -s 2 ".p";
select -ne :defaultRenderingList1;
select -ne :initialShadingGroup;
	setAttr -s 2 ".dsm";
	setAttr ".ro" yes;
select -ne :defaultResolution;
	setAttr ".pa" 1;
select -ne :defaultColorMgtGlobals;
	setAttr ".cme" no;
connectAttr "polySoftEdge1.out" "meshShape.i";
connectAttr "exprMesh.o[0]" "onMesh.t";
connectAttr "exprMesh.o[1]" "onMesh.r";
connectAttr "makeNurbTorus1.os" "surfaceShape.cr";
connectAttr "exprSurf.o[0]" "onSurface.t";
connectAttr "exprSurf.o[1]" "onSurface.r";
connectAttr "exprCurve.o[0]" "onCurve.t";
connectAttr "onCurve.pim" "exprCurve.i[0]";
connectAttr "curveShape.ws" "exprCurve.i[1]";
connectAttr "src.t" "exprCurve.i[2]";
connectAttr "src.pm" "exprCurve.i[3]";
connectAttr "onSurface.pim" "exprSurf.i[0]";
connectAttr "onSurface.ro" "exprSurf.i[1]";
connectAttr "transformGeometry2.og" "exprSurf.i[2]";
connectAttr "src.t" "exprSurf.i[3]";
connectAttr "src.pm" "exprSurf.i[4]";
connectAttr "surfaceShape.wm" "transformGeometry2.txf";
connectAttr "surfaceShape.l" "transformGeometry2.ig";
connectAttr "onMesh.pim" "exprMesh.i[0]";
connectAttr "onMesh.ro" "exprMesh.i[1]";
connectAttr "transformGeometry1.og" "exprMesh.i[2]";
connectAttr "src.t" "exprMesh.i[3]";
connectAttr "src.pm" "exprMesh.i[4]";
connectAttr "meshShape.o" "transformGeometry1.ig";
connectAttr "meshShape.wm" "transformGeometry1.txf";
connectAttr "polyTorus1.out" "polySoftEdge1.ip";
connectAttr "meshShape.wm" "polySoftEdge1.mp";
connectAttr "meshShape.iog" ":initialShadingGroup.dsm" -na;
connectAttr "surfaceShape.iog" ":initialShadingGroup.dsm" -na;
// End of closestPoints2016.ma
