//Maya ASCII 2012 scene
//Name: bend_roll.ma
//Codeset: 932
requires maya "2012";
requires "exprespy" "2.0.0.20161029";
currentUnit -l centimeter -a degree -t ntsc;
createNode joint -n "src";
	setAttr ".dla" yes;
createNode joint -n "srcEnd" -p "src";
	setAttr ".t" -type "double3" 5 0 0 ;
createNode joint -n "bend1";
	setAttr ".t" -type "double3" 0 0 2 ;
	setAttr ".dla" yes;
createNode joint -n "roll1" -p "bend1";
	setAttr ".t" -type "double3" 2 0 0 ;
	setAttr ".dla" yes;
createNode joint -n "end1" -p "roll1";
	setAttr ".t" -type "double3" 3 0 0 ;
createNode joint -n "roll2";
	setAttr ".t" -type "double3" 0 0 4 ;
	setAttr ".dla" yes;
createNode joint -n "bend2" -p "roll2";
	setAttr ".dla" yes;
createNode joint -n "end2" -p "bend2";
	setAttr ".t" -type "double3" 5 0 0 ;
createNode exprespy -n "composeRotExpr";
	addAttr -ci true -sn "method" -ln "method" -min 0 -max 1 -en "Stereographic Projection:Exponential Map" 
		-at "enum";
	addAttr -ci true -sn "reverseOrder" -ln "reverseOrder" -min 0 -max 1 -at "bool";
	setAttr ".cd" -type "string" (
		"if not COUNT:\n    from maya.api.OpenMaya import (\n        MVector, MQuaternion, MEulerRotation,\n    )\n    from math import sin, cos, tan\n\n    AT_ROLL = 0\n    AT_BENDH = 1\n    AT_BENDV = 2\n    AT_AXIS_ORIENT = 3\n    AT_ROTATE_ORDER = 4\n    METHOD = 10\n    AT_REVERSE_ORDER = 11\n\n    ZERO3 = (0., 0., 0.)\n    _X_VEC = MVector.kXaxisVector\n    _Y_VEC = MVector.kYaxisVector\n    _Z_VEC = MVector.kZaxisVector\n\n    def fromRollBendHV(rhv):\n        half = .5 * rhv[0]\n        f = sin(half)\n        quat = MQuaternion(_X_VEC[0] * f, _X_VEC[1] * f, _X_VEC[2] * f, cos(half))\n\n        h = tan(-.5 * rhv[1])\n        v = tan(.5 * rhv[2])\n        f = 2. / (h * h + v * v + 1.)\n        quat *= MQuaternion(_X_VEC, _X_VEC * (f - 1.) + _Y_VEC * (v * f) + _Z_VEC * (h * f))\n        return quat\n\nrhv = IN.get(AT_ROLL, 0.), IN.get(AT_BENDH, 0.), IN.get(AT_BENDV, 0.)\n\nreverse = IN.get(AT_REVERSE_ORDER, 0)\nif reverse:\n    rhv = (-rhv[0], -rhv[1], -rhv[2])\nif IN.get(METHOD, 0):\n    quat = MQuaternion(rhv[0] * .5, rhv[1] * .5, rhv[2] * .5, 0.).exp()\n"
		+ "else:\n    quat = fromRollBendHV(rhv)\nif reverse:\n    quat = quat.inverse()\n\noriQ = MEulerRotation(IN.get(AT_AXIS_ORIENT, ZERO3)).asQuaternion()\nquat = oriQ.inverse() * quat\nquat *= oriQ\n\nrot = MEulerRotation(ZERO3, IN.get(AT_ROTATE_ORDER, 0))\nrot.setValue(quat)\n\nOUT[0] = rot\n");
	setAttr -s 7 ".i";
	setAttr ".i[0]" 0;
	setAttr ".i[3]" -type "double3" 0 0 0 ;
createNode exprespy -n "decomposeRotExpr";
	addAttr -ci true -sn "method" -ln "method" -min 0 -max 1 -en "Stereographic Projection:Exponential Map" 
		-at "enum";
	addAttr -ci true -sn "reverseOrder" -ln "reverseOrder" -min 0 -max 1 -at "bool";
	setAttr ".cd" -type "string" (
		"if not COUNT:\n    from maya.api.OpenMaya import (\n        MVector, MQuaternion, MEulerRotation,\n    )\n    from math import atan2, pi as _PI\n\n    AT_ROTATE = 0\n    AT_ROTATE_ORDER = 1\n    AT_AXIS_ORIENT = 2\n    METHOD = 10\n    AT_REVERSE_ORDER = 11\n\n    ZERO3 = (0., 0., 0.)\n    _X_VEC = MVector.kXaxisVector\n    _Y_VEC = MVector.kYaxisVector\n    _Z_VEC = MVector.kZaxisVector\n\n    _2PI = 2. * _PI\n    boundAngle = lambda x: (x - _2PI) if x > _PI else ((x + _2PI) if x < -_PI else x)\n\n    def toRollBendHV(quat):\n        vec = _X_VEC.rotateBy(quat)\n        bendQ = MQuaternion(_X_VEC, vec)\n        b = (_X_VEC * vec) + 1.\n\n        rollQ = quat * bendQ.inverse()\n        return (\n            boundAngle(atan2(rollQ[0], rollQ[3]) * 2.),\n            atan2(_Z_VEC * vec, b) * -2.,\n            atan2(_Y_VEC * vec, b) * 2.,\n        )\n\nquat = MEulerRotation(IN.get(AT_AXIS_ORIENT, ZERO3)).asQuaternion()\noriQ = quat.inverse()\nquat *= MEulerRotation(IN.get(AT_ROTATE, ZERO3), IN.get(AT_ROTATE_ORDER, 0)).asQuaternion()\nquat *= oriQ\n\nreverse = IN.get(AT_REVERSE_ORDER, 0)\n"
		+ "if reverse:\n    quat = quat.inverse()\nif IN.get(METHOD, 0):\n    rhv = quat.log()\n    rhv = (rhv[0] * 2., rhv[1] * 2., rhv[2] * 2.)\nelse:\n    rhv = toRollBendHV(quat)\nif reverse:\n    rhv = (-rhv[0], -rhv[1], -rhv[2])\n\nOUT[0] = rhv[0]\nOUT[1] = rhv[1]\nOUT[2] = rhv[2]\n");
	setAttr -s 5 ".i";
	setAttr ".i[2]" -type "double3" 0 0 0 ;
	setAttr -s 3 ".o";
createNode exprespy -n "composeRotExpr1";
	addAttr -ci true -sn "method" -ln "method" -min 0 -max 1 -en "Stereographic Projection:Exponential Map" 
		-at "enum";
	addAttr -ci true -sn "reverseOrder" -ln "reverseOrder" -min 0 -max 1 -at "bool";
	setAttr ".cd" -type "string" (
		"if not COUNT:\n    from maya.api.OpenMaya import (\n        MVector, MQuaternion, MEulerRotation,\n    )\n    from math import sin, cos, tan\n\n    AT_ROLL = 0\n    AT_BENDH = 1\n    AT_BENDV = 2\n    AT_AXIS_ORIENT = 3\n    AT_ROTATE_ORDER = 4\n    METHOD = 10\n    AT_REVERSE_ORDER = 11\n\n    ZERO3 = (0., 0., 0.)\n    _X_VEC = MVector.kXaxisVector\n    _Y_VEC = MVector.kYaxisVector\n    _Z_VEC = MVector.kZaxisVector\n\n    def fromRollBendHV(rhv):\n        half = .5 * rhv[0]\n        f = sin(half)\n        quat = MQuaternion(_X_VEC[0] * f, _X_VEC[1] * f, _X_VEC[2] * f, cos(half))\n\n        h = tan(-.5 * rhv[1])\n        v = tan(.5 * rhv[2])\n        f = 2. / (h * h + v * v + 1.)\n        quat *= MQuaternion(_X_VEC, _X_VEC * (f - 1.) + _Y_VEC * (v * f) + _Z_VEC * (h * f))\n        return quat\n\nrhv = IN.get(AT_ROLL, 0.), IN.get(AT_BENDH, 0.), IN.get(AT_BENDV, 0.)\n\nreverse = IN.get(AT_REVERSE_ORDER, 0)\nif reverse:\n    rhv = (-rhv[0], -rhv[1], -rhv[2])\nif IN.get(METHOD, 0):\n    quat = MQuaternion(rhv[0] * .5, rhv[1] * .5, rhv[2] * .5, 0.).exp()\n"
		+ "else:\n    quat = fromRollBendHV(rhv)\nif reverse:\n    quat = quat.inverse()\n\noriQ = MEulerRotation(IN.get(AT_AXIS_ORIENT, ZERO3)).asQuaternion()\nquat = oriQ.inverse() * quat\nquat *= oriQ\n\nrot = MEulerRotation(ZERO3, IN.get(AT_ROTATE_ORDER, 0))\nrot.setValue(quat)\n\nOUT[0] = rot\n");
	setAttr -s 7 ".i";
	setAttr ".i[1]" 0;
	setAttr ".i[2]" 0;
	setAttr ".i[3]" -type "double3" 0 0 0 ;
createNode exprespy -n "composeRotExpr2";
	addAttr -ci true -sn "method" -ln "method" -min 0 -max 1 -en "Stereographic Projection:Exponential Map" 
		-at "enum";
	addAttr -ci true -sn "reverseOrder" -ln "reverseOrder" -min 0 -max 1 -at "bool";
	setAttr ".cd" -type "string" (
		"if not COUNT:\n    from maya.api.OpenMaya import (\n        MVector, MQuaternion, MEulerRotation,\n    )\n    from math import sin, cos, tan\n\n    AT_ROLL = 0\n    AT_BENDH = 1\n    AT_BENDV = 2\n    AT_AXIS_ORIENT = 3\n    AT_ROTATE_ORDER = 4\n    METHOD = 10\n    AT_REVERSE_ORDER = 11\n\n    ZERO3 = (0., 0., 0.)\n    _X_VEC = MVector.kXaxisVector\n    _Y_VEC = MVector.kYaxisVector\n    _Z_VEC = MVector.kZaxisVector\n\n    def fromRollBendHV(rhv):\n        half = .5 * rhv[0]\n        f = sin(half)\n        quat = MQuaternion(_X_VEC[0] * f, _X_VEC[1] * f, _X_VEC[2] * f, cos(half))\n\n        h = tan(-.5 * rhv[1])\n        v = tan(.5 * rhv[2])\n        f = 2. / (h * h + v * v + 1.)\n        quat *= MQuaternion(_X_VEC, _X_VEC * (f - 1.) + _Y_VEC * (v * f) + _Z_VEC * (h * f))\n        return quat\n\nrhv = IN.get(AT_ROLL, 0.), IN.get(AT_BENDH, 0.), IN.get(AT_BENDV, 0.)\n\nreverse = IN.get(AT_REVERSE_ORDER, 0)\nif reverse:\n    rhv = (-rhv[0], -rhv[1], -rhv[2])\nif IN.get(METHOD, 0):\n    quat = MQuaternion(rhv[0] * .5, rhv[1] * .5, rhv[2] * .5, 0.).exp()\n"
		+ "else:\n    quat = fromRollBendHV(rhv)\nif reverse:\n    quat = quat.inverse()\n\noriQ = MEulerRotation(IN.get(AT_AXIS_ORIENT, ZERO3)).asQuaternion()\nquat = oriQ.inverse() * quat\nquat *= oriQ\n\nrot = MEulerRotation(ZERO3, IN.get(AT_ROTATE_ORDER, 0))\nrot.setValue(quat)\n\nOUT[0] = rot\n");
	setAttr -s 7 ".i";
	setAttr ".i[1]" 0;
	setAttr ".i[2]" 0;
	setAttr ".i[3]" -type "double3" 0 0 0 ;
	setAttr ".reverseOrder" yes;
createNode exprespy -n "decomposeRotExpr1";
	addAttr -ci true -sn "method" -ln "method" -min 0 -max 1 -en "Stereographic Projection:Exponential Map" 
		-at "enum";
	addAttr -ci true -sn "reverseOrder" -ln "reverseOrder" -min 0 -max 1 -at "bool";
	setAttr ".cd" -type "string" (
		"if not COUNT:\n    from maya.api.OpenMaya import (\n        MVector, MQuaternion, MEulerRotation,\n    )\n    from math import atan2, pi as _PI\n\n    AT_ROTATE = 0\n    AT_ROTATE_ORDER = 1\n    AT_AXIS_ORIENT = 2\n    METHOD = 10\n    AT_REVERSE_ORDER = 11\n\n    ZERO3 = (0., 0., 0.)\n    _X_VEC = MVector.kXaxisVector\n    _Y_VEC = MVector.kYaxisVector\n    _Z_VEC = MVector.kZaxisVector\n    \n    _2PI = 2. * _PI\n    boundAngle = lambda x: (x - _2PI) if x > _PI else ((x + _2PI) if x < -_PI else x)\n\n    def toRollBendHV(quat):\n        vec = _X_VEC.rotateBy(quat)\n        bendQ = MQuaternion(_X_VEC, vec)\n        b = (_X_VEC * vec) + 1.\n\n        rollQ = quat * bendQ.inverse()\n        return (\n            boundAngle(atan2(rollQ[0], rollQ[3]) * 2.),\n            atan2(_Z_VEC * vec, b) * -2.,\n            atan2(_Y_VEC * vec, b) * 2.,\n        )\n\nquat = MEulerRotation(IN.get(AT_AXIS_ORIENT, ZERO3)).asQuaternion()\noriQ = quat.inverse()\nquat *= MEulerRotation(IN.get(AT_ROTATE, ZERO3), IN.get(AT_ROTATE_ORDER, 0)).asQuaternion()\nquat *= oriQ\n"
		+ "reverse = IN.get(AT_REVERSE_ORDER, 0)\nif reverse:\n    quat = quat.inverse()\nif IN.get(METHOD, 0):\n    rhv = quat.log()\n    rhv = (rhv[0] * 2., rhv[1] * 2., rhv[2] * 2.)\nelse:\n    rhv = toRollBendHV(quat)\nif reverse:\n    rhv = (-rhv[0], -rhv[1], -rhv[2])\n\nOUT[0] = rhv[0]\nOUT[1] = rhv[1]\nOUT[2] = rhv[2]\n");
	setAttr -s 5 ".i";
	setAttr ".i[2]" -type "double3" 0 0 0 ;
	setAttr -s 3 ".o";
	setAttr ".reverseOrder" yes;
createNode exprespy -n "composeRotExpr3";
	addAttr -ci true -sn "method" -ln "method" -min 0 -max 1 -en "Stereographic Projection:Exponential Map" 
		-at "enum";
	addAttr -ci true -sn "reverseOrder" -ln "reverseOrder" -min 0 -max 1 -at "bool";
	setAttr ".cd" -type "string" (
		"if not COUNT:\n    from maya.api.OpenMaya import (\n        MVector, MQuaternion, MEulerRotation,\n    )\n    from math import sin, cos, tan\n\n    AT_ROLL = 0\n    AT_BENDH = 1\n    AT_BENDV = 2\n    AT_AXIS_ORIENT = 3\n    AT_ROTATE_ORDER = 4\n    METHOD = 10\n    AT_REVERSE_ORDER = 11\n\n    ZERO3 = (0., 0., 0.)\n    _X_VEC = MVector.kXaxisVector\n    _Y_VEC = MVector.kYaxisVector\n    _Z_VEC = MVector.kZaxisVector\n\n    def fromRollBendHV(rhv):\n        half = .5 * rhv[0]\n        f = sin(half)\n        quat = MQuaternion(_X_VEC[0] * f, _X_VEC[1] * f, _X_VEC[2] * f, cos(half))\n\n        h = tan(-.5 * rhv[1])\n        v = tan(.5 * rhv[2])\n        f = 2. / (h * h + v * v + 1.)\n        quat *= MQuaternion(_X_VEC, _X_VEC * (f - 1.) + _Y_VEC * (v * f) + _Z_VEC * (h * f))\n        return quat\n\nrhv = IN.get(AT_ROLL, 0.), IN.get(AT_BENDH, 0.), IN.get(AT_BENDV, 0.)\n\nreverse = IN.get(AT_REVERSE_ORDER, 0)\nif reverse:\n    rhv = (-rhv[0], -rhv[1], -rhv[2])\nif IN.get(METHOD, 0):\n    quat = MQuaternion(rhv[0] * .5, rhv[1] * .5, rhv[2] * .5, 0.).exp()\n"
		+ "else:\n    quat = fromRollBendHV(rhv)\nif reverse:\n    quat = quat.inverse()\n\noriQ = MEulerRotation(IN.get(AT_AXIS_ORIENT, ZERO3)).asQuaternion()\nquat = oriQ.inverse() * quat\nquat *= oriQ\n\nrot = MEulerRotation(ZERO3, IN.get(AT_ROTATE_ORDER, 0))\nrot.setValue(quat)\n\nOUT[0] = rot\n");
	setAttr -s 7 ".i";
	setAttr ".i[0]" 0;
	setAttr ".i[3]" -type "double3" 0 0 0 ;
	setAttr ".reverseOrder" yes;
connectAttr "src.s" "srcEnd.is";
connectAttr "composeRotExpr.o[0]" "bend1.r";
connectAttr "bend1.s" "roll1.is";
connectAttr "composeRotExpr1.o[0]" "roll1.r";
connectAttr "roll1.s" "end1.is";
connectAttr "composeRotExpr2.o[0]" "roll2.r";
connectAttr "roll2.s" "bend2.is";
connectAttr "composeRotExpr3.o[0]" "bend2.r";
connectAttr "bend2.s" "end2.is";
connectAttr "decomposeRotExpr.o[1]" "composeRotExpr.i[1]";
connectAttr "decomposeRotExpr.o[2]" "composeRotExpr.i[2]";
connectAttr "bend1.ro" "composeRotExpr.i[4]";
connectAttr "composeRotExpr.method" "composeRotExpr.i[10]";
connectAttr "composeRotExpr.reverseOrder" "composeRotExpr.i[11]";
connectAttr "src.r" "decomposeRotExpr.i[0]";
connectAttr "src.ro" "decomposeRotExpr.i[1]";
connectAttr "decomposeRotExpr.method" "decomposeRotExpr.i[10]";
connectAttr "decomposeRotExpr.reverseOrder" "decomposeRotExpr.i[11]";
connectAttr "decomposeRotExpr.o[0]" "composeRotExpr1.i[0]";
connectAttr "roll1.ro" "composeRotExpr1.i[4]";
connectAttr "composeRotExpr1.method" "composeRotExpr1.i[10]";
connectAttr "composeRotExpr1.reverseOrder" "composeRotExpr1.i[11]";
connectAttr "decomposeRotExpr1.o[0]" "composeRotExpr2.i[0]";
connectAttr "roll2.ro" "composeRotExpr2.i[4]";
connectAttr "composeRotExpr2.method" "composeRotExpr2.i[10]";
connectAttr "composeRotExpr2.reverseOrder" "composeRotExpr2.i[11]";
connectAttr "src.r" "decomposeRotExpr1.i[0]";
connectAttr "src.ro" "decomposeRotExpr1.i[1]";
connectAttr "decomposeRotExpr1.method" "decomposeRotExpr1.i[10]";
connectAttr "decomposeRotExpr1.reverseOrder" "decomposeRotExpr1.i[11]";
connectAttr "decomposeRotExpr1.o[1]" "composeRotExpr3.i[1]";
connectAttr "decomposeRotExpr1.o[2]" "composeRotExpr3.i[2]";
connectAttr "bend2.ro" "composeRotExpr3.i[4]";
connectAttr "composeRotExpr3.method" "composeRotExpr3.i[10]";
connectAttr "composeRotExpr3.reverseOrder" "composeRotExpr3.i[11]";
// End of bend_roll.ma
