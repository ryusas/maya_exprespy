//Maya ASCII 2012 scene
//Name: bezierCurve.ma
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
createNode bezierCurve -n "curveShape" -p "curve";
	addAttr -ci true -sn "closed" -ln "closed" -min 0 -max 1 -at "bool";
	setAttr -k off ".v";
	setAttr ".tw" yes;
	setAttr ".dcv" yes;
	setAttr -cb on ".closed";
createNode exprespy -n "exprBezier";
	setAttr ".cd" -type "string" (
		"if not COUNT:\n    from maya.api.OpenMaya import MPoint, MMatrix\n\n    if hasattr(api, 'MFnNurbsCurve'):\n        #print('API 2.0')\n        from maya.api.OpenMaya import MFnNurbsCurve, MFnNurbsCurveData\n        kOpen = MFnNurbsCurve.kOpen\n\n        def createData(pnts, knots):\n            data = MFnNurbsCurveData().create()\n            MFnNurbsCurve().create(pnts, knots, 3, kOpen, False, True, data)\n            return data\n\n    else:\n        #print('API 1.0')\n        from maya.OpenMaya import (\n            MFnNurbsCurve, MFnNurbsCurveData, MPointArray, MDoubleArray,\n        )\n        kOpen = MFnNurbsCurve.kOpen\n\n        def convToMDoubleArray(vals):\n            arr = MDoubleArray()\n            arr.setLength(len(vals))\n            for i, v in enumerate(vals):\n                arr[i] = v\n            return arr\n\n        def convToMPointArray(vals):\n            arr = MPointArray()\n            arr.setLength(len(vals))\n            for i, v in enumerate(vals):\n                p = arr[i]\n                p.x, p.y, p.z, p.w = v\n"
		+ "            return arr\n\n        def createData(pnts, knots):\n            data = MFnNurbsCurveData().create()\n            MFnNurbsCurve().create(\n                convToMPointArray(pnts), convToMDoubleArray(knots),\n                3, kOpen, False, True, data)\n            return data\n\n    def xformAtPoint(m):\n        res = MMatrix([\n            1., 0., 0., 0.,\n            0., 1., 0., 0.,\n            0., 0., 1., 0.,\n            -m[12], -m[13], -m[14], 1.\n        ])\n        res *= m\n        return res\n\n    def calcTangent(p0, p1, p2):\n        vb = p1 - p0\n        vf = p2 - p1\n        lb = vb.length() / 3\n        lf = vf.length() / 3 \n        vb.normalize()\n        vf.normalize()\n        vb += vf\n        vb.normalize()\n        return p1 - vb * lb, p1, p1 + vb * lf\n\n    def calcStartTangent(p1, p2b, p2):\n        vf = (p2b - p1).normalize()\n        vf *= (p2 - p1).length() / 3\n        return p1, p1 + vf\n\n    def calcEndTangent(p0, p0f, p1):\n        vb = (p1 - p0f).normalize()\n        vb *= (p1 - p0).length() / 3\n        return p1 - vb, p1\n\n"
		+ "    def compute(closed, inMs):\n        nInPnts = len(inMs)\n        if nInPnts < 2:\n            return MFnNurbsCurveData().create()\n\n        # Decides the knot vector and the CV array allocation.\n        nKnots = nInPnts * 3\n        if closed:\n            nKnots += 3\n        knots = [i // 3 for i in range(nKnots)]\n\n        nPnts = nKnots - 2\n        pnts = [None] * nPnts\n        inPs = [MPoint(m[12], m[13], m[14]) for m in inMs]\n\n        # Calculates the tangents at other than the start and end points.\n        idxRange = range(1, nInPnts - 1)\n        if idxRange:\n            for idx in idxRange:\n                i = idx * 3 - 1\n                pnts[i:i + 3] = calcTangent(inPs[idx - 1], inPs[idx], inPs[idx + 1])\n        else:\n            idx = 0\n            pnts[1] = inPs[0]\n\n        # Calculates the tangents at the start and end points, and transforms them.\n        idx += 1\n        i = idx * 3 - 1\n        if closed:\n            # At the end point.\n            pnts[i:i + 3] = calcTangent(inPs[idx - 1], inPs[idx], inPs[0])\n"
		+ "            m = xformAtPoint(inMs[idx])\n            pnts[i] *= m\n            pnts[i + 2] *= m\n\n            # At the start point.\n            pnts[i + 3], pnts[0], pnts[1] = calcTangent(inPs[-1], inPs[0], inPs[1])\n            m = xformAtPoint(inMs[0])\n            pnts[i + 3] *= m\n            pnts[1] *= m\n            pnts[i + 4] = inPs[0]\n\n        else:\n            # At the end point.\n            pnts[i:i + 2] = calcEndTangent(inPs[idx - 1], pnts[i - 1], inPs[idx])\n            pnts[i] *= xformAtPoint(inMs[idx])\n\n            # At the start point.\n            pnts[:2] = calcStartTangent(inPs[0], pnts[2], inPs[1])\n            pnts[1] *= xformAtPoint(inMs[0])\n\n        # Transforms the rest tangents.\n        for idx in idxRange:\n            m = xformAtPoint(inMs[idx])\n            i = idx * 3 - 1\n            pnts[i] *= m\n            pnts[i + 2] *= m\n\n        return createData(pnts, knots)\n\nOUT[0] = compute(IN[0], [IN[x] for x in sorted([x for x in IN if x]) if IN[x]])\n");
	setAttr -s 6 ".i";
connectAttr "exprBezier.o[0]" "curveShape.cr";
connectAttr "curveShape.closed" "exprBezier.i[0]";
connectAttr "P0.m" "exprBezier.i[1]";
connectAttr "P1.m" "exprBezier.i[2]";
connectAttr "P2.m" "exprBezier.i[3]";
connectAttr "P3.m" "exprBezier.i[4]";
connectAttr "P4.m" "exprBezier.i[5]";
// End of bezierCurve.ma
