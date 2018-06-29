//Maya ASCII 2012 scene
//Name: closestPoints.ma
//Codeset: 932
requires maya "2012";
requires "exprespy" "2.0.0.20161029";
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
createNode exprespy -n "exprMesh";
	setAttr ".cd" -type "string" (
		"if not COUNT:\n    from maya.api.OpenMaya import (\n        MPoint, MVector, MMatrix, MEulerRotation)\n    from maya.OpenMaya import (\n        MMeshIntersector as MMeshIntersector1,\n        MFnGeometryData as MFnGeometryData1,\n        MPointOnMesh as MPointOnMesh1,\n        MFnMesh as MFnMesh1,\n        MMatrix as MMatrix1,\n        MPoint as MPoint1,\n        MVector as MVector1,\n        MScriptUtil,\n    )\n    kWorld1 = api1.MSpace.kWorld\n    su_getIA = MScriptUtil.getIntArrayItem\n    su_getF = MScriptUtil.getFloat\n\n    def getClosestPoint(mesh, pos):\n        mi = MMeshIntersector1()\n        m = MMatrix1()\n        MFnGeometryData1(mesh).getMatrix(m)\n        mi.create(mesh, m)\n        pom = MPointOnMesh1()\n        mi.getClosestPoint(MPoint1(pos.x, pos.y, pos.z), pom)\n        p = pom.getPoint()\n        p = MPoint1(p.x, p.y, p.z)\n        p *= m\n        return MPoint(p.x, p.y, p.z), pom\n\n    if hasattr(MPointOnMesh1, 'getBarycentricCoords'):\n        def createMatrix(mesh, pom):\n            msuu = MScriptUtil()\n            pu = msuu.asFloatPtr()\n"
		+ "            msuv = MScriptUtil()\n            pv = msuv.asFloatPtr()\n            pom.getBarycentricCoords(pu, pv)\n            bu = su_getF(pu)\n            bv = su_getF(pv)\n    \n            face = pom.faceIndex()\n            fn1 = MFnMesh1(mesh)\n            msut = MScriptUtil()\n            msut.createFromInt(0, 0, 0)\n            pt = msut.asIntPtr()\n            fn1.getPolygonTriangleVertices(face, pom.triangleIndex(), pt)\n            v0 = MVector1()\n            fn1.getFaceVertexTangent(face, su_getIA(pt, 0), v0, kWorld1)\n            v1 = MVector1()\n            fn1.getFaceVertexTangent(face, su_getIA(pt, 1), v1, kWorld1)\n            v2 = MVector1()\n            fn1.getFaceVertexTangent(face, su_getIA(pt, 2), v2, kWorld1)\n    \n            vx = v2 + (v0 - v2) * bu + (v1 - v2) * bv\n            vx.normalize()\n            vy = MVector1(pom.getNormal())\n            vy.normalize()\n            vz = vx ^ vy\n            return MMatrix([\n                vx.x, vx.y, vx.z, 0.,\n                vy.x, vy.y, vy.z, 0.,\n                vz.x, vz.y, vz.z, 0.,\n"
		+ "                0., 0., 0., 1.\n            ])\n    \n        def compute(mesh, srcPos):\n            pos, pom = getClosestPoint(mesh, srcPos)\n            pos *= IN[0]\n            OUT[0] = pos\n    \n            m = createMatrix(mesh, pom)\n            m *= IN[0]\n            rot = MEulerRotation([0., 0., 0.], IN[1])\n            rot.setValue(m)\n            OUT[1] = rot\n\n    else:\n        def compute(mesh, srcPos):\n            pos, pom = getClosestPoint(mesh, srcPos)\n            pos *= IN[0]\n            OUT[0] = pos\n            OUT[1] = [0., 0., 0.]\n\ncompute(\n    IN[2],\n    MPoint(IN[3]) * IN[4])");
	setAttr ".iaa1o" yes;
	setAttr -s 5 ".i";
	setAttr -s 2 ".o";
createNode polySoftEdge -n "polySoftEdge1";
	setAttr ".uopa" yes;
	setAttr ".ics" -type "componentList" 1 "e[*]";
	setAttr ".ix" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1;
	setAttr ".a" 59.999999999999993;
createNode polyTorus -n "polyTorus1";
	setAttr ".r" 3;
	setAttr ".sr" 1;
	setAttr ".sh" 8;
createNode exprespy -n "exprSurf";
	setAttr ".cd" -type "string" (
		"if not COUNT:\n    from maya.api.OpenMaya import MPoint, MMatrix, MEulerRotation\n    from maya.OpenMaya import (\n        MFnNurbsSurface as MFnNurbsSurface1,\n        MPoint as MPoint1,\n        MVector as MVector1,\n        MScriptUtil,\n    )\n    kWorld1 = api1.MSpace.kWorld\n    su_getD = MScriptUtil.getDouble\n\n    def getClosestPoint(fn1, pos):\n        msuu = MScriptUtil()\n        pu = msuu.asDoublePtr()\n        msuv = MScriptUtil()\n        pv = msuv.asDoublePtr()\n        p = fn1.closestPoint(MPoint1(pos.x, pos.y, pos.z), pu, pv, False, 1.e-3, kWorld1)\n        return MPoint(p.x, p.y, p.z), su_getD(pu), su_getD(pv)\n\n    def compute(surface, srcPos):\n        fn1 = MFnNurbsSurface1(surface)\n        pos, u, v = getClosestPoint(fn1, srcPos)\n        pos *= IN[0]\n        OUT[0] = pos\n\n        vy = fn1.normal(u, v)\n        vx = MVector1()\n        vz = MVector1()\n        fn1.getTangents(u, v, vx, vz)\n        vx.normalize()\n        vz = vx ^ vy\n        m = MMatrix([\n            vx.x, vx.y, vx.z, 0.,\n            vy.x, vy.y, vy.z, 0.,\n"
		+ "            vz.x, vz.y, vz.z, 0.,\n            0., 0., 0., 1.\n        ])\n        m *= IN[0]\n        rot = MEulerRotation([0., 0., 0.], IN[1])\n        rot.setValue(m)\n        OUT[1] = rot\n\ncompute(\n    IN[2],\n    MPoint(IN[3]) * IN[4])");
	setAttr ".iaa1o" yes;
	setAttr -s 5 ".i";
	setAttr -s 2 ".o";
createNode makeNurbTorus -n "makeNurbTorus1";
	setAttr ".ax" -type "double3" 0 1 0 ;
	setAttr ".r" 3;
	setAttr ".nsp" 4;
	setAttr ".hr" 0.33333333333333331;
createNode exprespy -n "exprCurve";
	setAttr ".cd" -type "string" "if not COUNT:\n    from maya.api.OpenMaya import MPoint\n    from maya.OpenMaya import (\n        MFnNurbsCurve as MFnNurbsCurve1,\n        MPoint as MPoint1,\n        MScriptUtil,\n    )\n    kWorld1 = api1.MSpace.kWorld\n\n    def getClosestPoint(fn1, pos):\n        msuu = MScriptUtil()\n        pu = msuu.asDoublePtr()\n        p = fn1.closestPoint(MPoint1(pos.x, pos.y, pos.z), pu, 1.e-3, kWorld1)\n        return MPoint(p.x, p.y, p.z), MScriptUtil.getDouble(pu)\n\n    def compute(curve, srcPos):\n        fn1 = MFnNurbsCurve1(curve)\n        pos, u = getClosestPoint(fn1, srcPos)\n        pos *= IN[0]\n        OUT[0] = pos\n\ncompute(\n    IN[1],\n    MPoint(IN[2]) * IN[3])";
	setAttr ".iaa1o" yes;
	setAttr -s 4 ".i";
select -ne :initialShadingGroup;
	setAttr -s 2 ".dsm";
	setAttr ".ro" yes;
connectAttr "polySoftEdge1.out" "meshShape.i";
connectAttr "exprMesh.o[0]" "onMesh.t";
connectAttr "exprMesh.o[1]" "onMesh.r";
connectAttr "makeNurbTorus1.os" "surfaceShape.cr";
connectAttr "exprSurf.o[0]" "onSurface.t";
connectAttr "exprSurf.o[1]" "onSurface.r";
connectAttr "exprCurve.o[0]" "onCurve.t";
connectAttr "onMesh.pim" "exprMesh.i[0]";
connectAttr "onMesh.ro" "exprMesh.i[1]";
connectAttr "meshShape.w" "exprMesh.i[2]";
connectAttr "src.t" "exprMesh.i[3]";
connectAttr "src.pm" "exprMesh.i[4]";
connectAttr "polyTorus1.out" "polySoftEdge1.ip";
connectAttr "meshShape.wm" "polySoftEdge1.mp";
connectAttr "onSurface.pim" "exprSurf.i[0]";
connectAttr "onSurface.ro" "exprSurf.i[1]";
connectAttr "surfaceShape.ws" "exprSurf.i[2]";
connectAttr "src.t" "exprSurf.i[3]";
connectAttr "src.pm" "exprSurf.i[4]";
connectAttr "onCurve.pim" "exprCurve.i[0]";
connectAttr "curveShape.ws" "exprCurve.i[1]";
connectAttr "src.t" "exprCurve.i[2]";
connectAttr "src.pm" "exprCurve.i[3]";
connectAttr "meshShape.iog" ":initialShadingGroup.dsm" -na;
connectAttr "surfaceShape.iog" ":initialShadingGroup.dsm" -na;
// End of closestPoints.ma
