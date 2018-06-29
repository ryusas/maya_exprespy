//Maya ASCII 2012 scene
//Name: epcurve.ma
//Codeset: 932
requires maya "2012";
requires "exprespy" "2.0.0.20161029";
currentUnit -l centimeter -a degree -t ntsc;
createNode transform -n "space";
createNode transform -n "P0" -p "space";
createNode locator -n "P0Shape" -p "P0";
	setAttr -k off ".v";
	setAttr ".los" -type "double3" 2 2 2 ;
createNode transform -n "P1" -p "space";
	setAttr ".t" -type "double3" 5 0 0 ;
createNode locator -n "P1Shape" -p "P1";
	setAttr -k off ".v";
	setAttr ".los" -type "double3" 2 2 2 ;
createNode transform -n "P2" -p "space";
	setAttr ".t" -type "double3" 10 0 0 ;
createNode locator -n "P2Shape" -p "P2";
	setAttr -k off ".v";
	setAttr ".los" -type "double3" 2 2 2 ;
createNode transform -n "P3" -p "space";
	setAttr ".t" -type "double3" 15 0 0 ;
createNode locator -n "P3Shape" -p "P3";
	setAttr -k off ".v";
	setAttr ".los" -type "double3" 2 2 2 ;
createNode transform -n "P4" -p "space";
	setAttr ".t" -type "double3" 20 0 0 ;
createNode locator -n "P4Shape" -p "P4";
	setAttr -k off ".v";
	setAttr ".los" -type "double3" 2 2 2 ;
createNode transform -n "curve" -p "space";
	addAttr -ci true -sn "closed" -ln "closed" -min 0 -max 1 -at "bool";
	addAttr -ci true -sn "degree" -ln "degree" -dv 3 -min 1 -smx 7 -at "short";
	setAttr -cb on ".closed";
	setAttr -cb on ".degree";
createNode nurbsCurve -n "curveShape" -p "curve";
	setAttr -k off ".v";
	setAttr ".tw" yes;
	setAttr ".dcv" yes;
createNode exprespy -n "exprBezier";
	setAttr ".cd" -type "string" (
		"if not COUNT:\n    if hasattr(api, 'MFnNurbsCurve'):\n        #print('API 2.0')\n        from maya.api.OpenMaya import (\n            MFnNurbsCurve, MFnNurbsCurveData, MPoint,\n        )\n\n        def createEPCurve(trns, form, degree):\n            data = MFnNurbsCurveData().create()\n            MFnNurbsCurve().createWithEditPoints(\n                [MPoint(t) for t in trns],\n                degree, form, False, True, True, data)\n            return data\n\n    else:\n        #print('API 1.0')\n        from maya.OpenMaya import (\n            MFnNurbsCurve, MFnNurbsCurveData, MPointArray,\n        )\n        kOpen = MFnNurbsCurve.kOpen\n\n        def convToMPointArray(vals):\n            arr = MPointArray()\n            arr.setLength(len(vals))\n            for i, v in enumerate(vals):\n                p = arr[i]\n                p.x, p.y, p.z = v\n            return arr\n\n        def createEPCurve(trns, form, degree):\n            data = MFnNurbsCurveData().create()\n            MFnNurbsCurve().createWithEditPoints(\n                convToMPointArray(trns),\n"
		+ "                degree, form, False, True, True, data)\n            return data\n\n    def compute(trns, closed, degree):\n        num = len(trns)\n        if num < 2:\n            return MFnNurbsCurveData().create()\n        if closed:\n            trns.append(trns[0])\n            return createEPCurve(trns, kPeriodic, degree)\n        return createEPCurve(trns, kOpen, degree)\n\n    kOpen = MFnNurbsCurve.kOpen\n    kPeriodic = MFnNurbsCurve.kPeriodic\n\nOUT[0] = compute(\n    [IN[x] for x in sorted([x for x in IN if x >= 2]) if IN[x]],\n    IN[0], IN[1],\n)\n");
	setAttr -s 7 ".i";
connectAttr "exprBezier.o[0]" "curveShape.cr";
connectAttr "curve.closed" "exprBezier.i[0]";
connectAttr "curve.degree" "exprBezier.i[1]";
connectAttr "P0.t" "exprBezier.i[2]";
connectAttr "P1.t" "exprBezier.i[3]";
connectAttr "P2.t" "exprBezier.i[4]";
connectAttr "P3.t" "exprBezier.i[5]";
connectAttr "P4.t" "exprBezier.i[6]";
// End of epcurve.ma
