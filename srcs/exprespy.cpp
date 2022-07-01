#include <Python.h>

#include <maya/MFnPlugin.h>
#include <maya/MGlobal.h>
#include <maya/MPxNode.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MFnGenericAttribute.h>
#include <maya/MFnNumericData.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnNumericData.h>
#include <maya/MFnMatrixData.h>
#include <maya/MDataBlock.h>
#include <maya/MArrayDataHandle.h>
#include <maya/MVector.h>
#include <maya/MMatrix.h>
#include <maya/MFnDependencyNode.h>

#ifdef _WIN32
#pragma warning(disable: 4127)
#endif

#define EXPRESPY_NODE_ID  0x00070004  // もし何かと衝突するなら書き換えること。(Free: 0x00000000 ～ 0x0007ffff)

#if PY_MAJOR_VERSION < 3
    // py2 では io.StringIO ではなく StringIO.StringIO を使用することで str と unicode に両対応させる。
    // cStringIO にしないのは unicode を通すため。
    #define STRINGIO_MODULE         "StringIO"
    #define BUILTINS_MODULE_NAME    "__builtin__"
    #define PYINT_fromLong  PyInt_FromLong
    #define PYSTR_fromChar  PyString_FromString
    #define PYBYTES_asChar  PyString_AsString
    #define PYBYTES_check   PyString_Check
    #define PYBYTES_SIZE    PyString_GET_SIZE
#else
    // py3 では io.StringIO を使用し unicode のみに対応する。
    #define STRINGIO_MODULE         "io"
    #define BUILTINS_MODULE_NAME    "builtins"
    #define PYINT_fromLong  PyLong_FromLong
    #define PYSTR_fromChar  PyUnicode_FromString
    #define PYBYTES_asChar  PyBytes_AsString
    #define PYBYTES_check   PyBytes_Check
    #define PYBYTES_SIZE    PyBytes_GET_SIZE
#endif


//=============================================================================
/// Functions.
//=============================================================================
/// モジュールをインポートする。PyImport_ImportModule より高水準。
static inline PyObject* _importModule(const char* name)
{
    PyObject* nameo = PYSTR_fromChar(name);
    if (nameo) {
        PyObject* mod = PyImport_Import(nameo);
        Py_DECREF(nameo);
        return mod;
    }
    return NULL;
}

/// dict から type オブジェクトを得る。
static inline PyObject* _getTypeObject(PyObject* dict, const char* name)
{
    PyObject* o = PyDict_GetItemString(dict, name);
    return PyType_Check(o) ? o : NULL;
}

/// 値の参照を奪いつつ dict に値をセットする。
static inline void _setDictStealValue(PyObject* dic, const char* key, PyObject* valo)
{
    if (valo) {
        PyDict_SetItemString(dic, key, valo);
        Py_DECREF(valo);
    } else {
        PyDict_SetItemString(dic, key, Py_None);
    }
}

/// キーと値の参照を奪いつつ I/O 用 dict に値をセットする。
static inline void _setIODictStealValue(PyObject* dic, PyObject* keyo, PyObject* valo)
{
    if (valo) {
        PyDict_SetItem(dic, keyo, valo);
        Py_DECREF(valo);
    } else {
        PyDict_SetItem(dic, keyo, Py_None);
    }
    Py_DECREF(keyo);
}

/// dict に int をキーとして PyObject* をセットする。
static inline void _setDictValue(PyObject* dic, int key, PyObject* valo)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        PyDict_SetItem(dic, keyo, valo);
        Py_DECREF(keyo);
    }
}

/// dict から int をキーとして PyObject* を得る。
static inline PyObject* _getDictValue(PyObject* dic, int key)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        PyObject* valo = PyDict_GetItem(dic, keyo);
        Py_DECREF(keyo);
        return valo;
    }
    return NULL;
}

/// 型判別済みの sequence の PyObject* から double3 の data を得る。
static inline MObject _getDouble3Value(PyObject* valo)
{
    MFnNumericData fnOutData;
    MObject data = fnOutData.create(MFnNumericData::k3Double);
    fnOutData.setData(
        PyFloat_AS_DOUBLE(PySequence_GetItem(valo, 0)),
        PyFloat_AS_DOUBLE(PySequence_GetItem(valo, 1)),
        PyFloat_AS_DOUBLE(PySequence_GetItem(valo, 2))
    );
    return data;
}

/// 型判別済みの sequence の PyObject* から double4 の data を得る。
static inline MObject _getDouble4Value(PyObject* valo)
{
    MFnNumericData fnOutData;
    MObject data = fnOutData.create(MFnNumericData::k4Double);
    fnOutData.setData(
        PyFloat_AS_DOUBLE(PySequence_GetItem(valo, 0)),
        PyFloat_AS_DOUBLE(PySequence_GetItem(valo, 1)),
        PyFloat_AS_DOUBLE(PySequence_GetItem(valo, 2)),
        PyFloat_AS_DOUBLE(PySequence_GetItem(valo, 3))
    );
    return data;
}

/// 型判別済みの sequence の PyObject* から float3 の data を得る。
static inline MObject _getFloat3Value(PyObject* valo)
{
    MFnNumericData fnOutData;
    MObject data = fnOutData.create(MFnNumericData::k3Float);
    fnOutData.setData(
        static_cast<float>(PyFloat_AS_DOUBLE(PySequence_GetItem(valo, 0))),
        static_cast<float>(PyFloat_AS_DOUBLE(PySequence_GetItem(valo, 1))),
        static_cast<float>(PyFloat_AS_DOUBLE(PySequence_GetItem(valo, 2)))
    );
    return data;
}

/// sequence の PyObject* から double2, double3, double4, long2, long3 のいずれかを得る。
static inline MObject _getTypedSequence(PyObject* valo)
{
    MObject data;

    Py_ssize_t num = PySequence_Length(valo);
    if (num < 2 || 4 < num) return data;

    bool hasFloat = false;
    int ival[4];
    double fval[4];
    for (Py_ssize_t i=0; i<num; ++i) {
        PyObject* v = PySequence_GetItem(valo, i);
        if (PyFloat_Check(v)) {
            hasFloat = true;
            fval[i] = PyFloat_AS_DOUBLE(v);
#if PY_MAJOR_VERSION < 3
        } else if (PyInt_Check(v)) {
            ival[i] = PyInt_AS_LONG(v);
            fval[i] = static_cast<double>(ival[i]);
#endif
        } else if (PyLong_Check(v)) {
            ival[i] = static_cast<int>(PyLong_AsLong(v));  // TODO: OverflowError 対策。
            fval[i] = static_cast<double>(ival[i]);

        } else {
            return data;
        }
    }

    MFnNumericData fnOutData;
    switch (num) {
    case 2:
        if (hasFloat) {
            data = fnOutData.create(MFnNumericData::k2Double);
            fnOutData.setData(fval[0], fval[1]);
        } else {
            data = fnOutData.create(MFnNumericData::k2Long);
            fnOutData.setData(ival[0], ival[1]);
        }
        break;
    case 3:
        if (hasFloat) {
            data = fnOutData.create(MFnNumericData::k3Double);
            fnOutData.setData(fval[0], fval[1], fval[2]);
        } else {
            data = fnOutData.create(MFnNumericData::k3Long);
            fnOutData.setData(ival[0], ival[1], ival[2]);
        }
        break;
    case 4:
        data = fnOutData.create(MFnNumericData::k4Double);
        fnOutData.setData(fval[0], fval[1], fval[2], fval[3]);
        break;
    }
    return data;
}

/// 型判別済みの PyObject* の値を MMatrix に得る。
static inline void _getMatrixValueFromPyObject(MMatrix& mat, PyObject* valo)
{
    PyObject* getElement = PyObject_GetAttrString(valo, "getElement");
    if (getElement) {
        PyObject* idxs[] = {
            PYINT_fromLong(0), PYINT_fromLong(1), PYINT_fromLong(2), PYINT_fromLong(3)
        };
        PyObject* args = PyTuple_New(2);
        for (unsigned i=0; i<4; ++i) {
            PyTuple_SET_ITEM(args, 0, idxs[i]);
            for (unsigned j=0; j<4; ++j) {
                PyTuple_SET_ITEM(args, 1, idxs[j]);

                PyObject* vo = PyObject_CallObject(getElement, args);
                //PyObject* vo = PyObject_CallFunction(getElement, "(ii)", i, j);
                if (vo) {
                    mat.matrix[i][j] = PyFloat_AS_DOUBLE(vo);
                    Py_DECREF(vo);
                } else {
                    mat.matrix[i][j] = MMatrix::identity[i][j];
                }
            }
        }

        PyTuple_SET_ITEM(args, 0, idxs[0]);
        PyTuple_SET_ITEM(args, 1, idxs[1]);
        Py_DECREF(args);
        Py_DECREF(idxs[2]);
        Py_DECREF(idxs[3]);

    } else {
        mat.setToIdentity();
    }
}


//=============================================================================
/// Exprespy node class.
//=============================================================================
class Exprespy : public MPxNode {
    PyObject* _base_globals;
    PyObject* _input;
    PyObject* _output;
    PyObject* _globals;
    PyCodeObject* _codeobj;
    PyObject* _mplug2_input;
    PyObject* _mplug2_output;
    PyObject* _mplug1_input;
    PyObject* _mplug1_output;

    PyObject* _api2_dict;
    PyObject* _type2_MVector;
    PyObject* _type2_MPoint;
    PyObject* _type2_MEulerRotation;
    PyObject* _type2_MMatrix;
    PyObject* _type2_MObject;
    PyObject* _type2_MQuaternion;
    PyObject* _type2_MColor;
    PyObject* _type2_MFloatVector;
    PyObject* _type2_MFloatPoint;

    PyObject* _api1_dict;
    PyObject* _type1_MObject;

    PyObject* _type_StringIO;
    PyObject* _sys_dict;
    PyObject* _sys_stdout;
    PyObject* _sys_stderr;

    int _count;

    MStatus _compileCode(MDataBlock&);
    MStatus _executeCode(MDataBlock&);

    void _printPythonError();

    void _setInputScalar(int key, const double& val);
    void _setInputString(int key, const MString& str);
    void _setInputShort2(int key, MObject& data);
    void _setInputShort3(int key, MObject& data);
    void _setInputLong2(int key, MObject& data);
    void _setInputLong3(int key, MObject& data);
    void _setInputFloat2(int key, MObject& data);
    void _setInputFloat3(int key, MObject& data);
    void _setInputDouble2(int key, MObject& data);
    void _setInputDouble3(int key, MObject& data);
    void _setInputDouble4(int key, MObject& data);
    void _setInputVector3(int key, MObject& data);
    void _setInputMatrix(int key, MObject& data);

    void _setInputMObject2(int key);
    void _setOutputMObject2(int key, PyObject* valo);
    void _preparePyPlug2();

    void _setInputMObject1(int key);
    void _setOutputMObject1(int key, PyObject* valo);
    void _preparePyPlug1();

public:
    static MTypeId id;
    static MString name;

    static MObject aCode;
    static MObject aInputsAsApi1Object;
    static MObject aCompiled;
    static MObject aInput;
    static MObject aOutput;

    static void* creator() { return new Exprespy; }
    static MStatus initialize();

    Exprespy();
    virtual ~Exprespy();

    MStatus compute(const MPlug&, MDataBlock&);

#if MAYA_API_VERSION >= 20160000
    SchedulingType schedulingType () const { return MPxNode::kGloballySerial; }
#endif
};

MTypeId Exprespy::id(EXPRESPY_NODE_ID);
MString Exprespy::name("exprespy");
MObject Exprespy::aCode;
MObject Exprespy::aInputsAsApi1Object;
MObject Exprespy::aCompiled;
MObject Exprespy::aInput;
MObject Exprespy::aOutput;


//------------------------------------------------------------------------------
/// Static: Initialization.
//------------------------------------------------------------------------------
MStatus Exprespy::initialize()
{
    MFnTypedAttribute fnTyped;
    MFnNumericAttribute fnNumeric;
    MFnGenericAttribute fnGeneric;

    // code
    aCode = fnTyped.create("code", "cd", MFnData::kString);
    fnTyped.setConnectable(false);
    CHECK_MSTATUS_AND_RETURN_IT( addAttribute(aCode) );

    // inputsAsApi1Object
    aInputsAsApi1Object = fnNumeric.create("inputsAsApi1Object", "iaa1o", MFnNumericData::kBoolean, false);
    fnTyped.setConnectable(false);
    CHECK_MSTATUS_AND_RETURN_IT( addAttribute(aInputsAsApi1Object) );

    // compiled
    aCompiled = fnNumeric.create("compile", "cm", MFnNumericData::kBoolean, false);
    fnNumeric.setWritable(false);
    fnNumeric.setStorable(false);
    fnNumeric.setHidden(true);
    CHECK_MSTATUS_AND_RETURN_IT( addAttribute(aCompiled) );

    // input
    aInput = fnGeneric.create("input", "i");
    // 入力の場合は kAny だけでコネクトは全て許容されるが setAttr では弾かれてしまうので、結局全ての列挙が必要。
    fnGeneric.addDataAccept(MFnData::kAny);
    fnGeneric.addDataAccept(MFnData::kNumeric);  // これは無くても大丈夫そうだが一応。
    fnGeneric.addNumericDataAccept(MFnNumericData::k2Short);
    fnGeneric.addNumericDataAccept(MFnNumericData::k3Short);
    fnGeneric.addNumericDataAccept(MFnNumericData::k2Long);
    fnGeneric.addNumericDataAccept(MFnNumericData::k3Long);
    fnGeneric.addNumericDataAccept(MFnNumericData::k2Float);
    fnGeneric.addNumericDataAccept(MFnNumericData::k3Float);
    fnGeneric.addNumericDataAccept(MFnNumericData::k2Double);
    fnGeneric.addNumericDataAccept(MFnNumericData::k3Double);
    fnGeneric.addNumericDataAccept(MFnNumericData::k4Double);
    fnGeneric.addDataAccept(MFnData::kPlugin);
    fnGeneric.addDataAccept(MFnData::kPluginGeometry);
    fnGeneric.addDataAccept(MFnData::kString);
    fnGeneric.addDataAccept(MFnData::kMatrix);
    fnGeneric.addDataAccept(MFnData::kStringArray);
    fnGeneric.addDataAccept(MFnData::kDoubleArray);
    fnGeneric.addDataAccept(MFnData::kIntArray);
    fnGeneric.addDataAccept(MFnData::kPointArray);
    fnGeneric.addDataAccept(MFnData::kVectorArray);
    fnGeneric.addDataAccept(MFnData::kComponentList);
    fnGeneric.addDataAccept(MFnData::kMesh);
    fnGeneric.addDataAccept(MFnData::kLattice);
    fnGeneric.addDataAccept(MFnData::kNurbsCurve);
    fnGeneric.addDataAccept(MFnData::kNurbsSurface);
    fnGeneric.addDataAccept(MFnData::kSphere);
    fnGeneric.addDataAccept(MFnData::kDynArrayAttrs);
    fnGeneric.addDataAccept(MFnData::kSubdSurface);
    // 以下はクラッシュする。
    //fnGeneric.addDataAccept(MFnData::kDynSweptGeometry);
    //fnGeneric.addDataAccept(MFnData::kNObject);
    //fnGeneric.addDataAccept(MFnData::kNId);

    fnGeneric.setArray(true);
    CHECK_MSTATUS_AND_RETURN_IT(addAttribute(aInput));

    // output
    aOutput = fnGeneric.create("output", "o");
    // 出力の場合は kAny だけでは Numeric と NumericData 以外のコネクトは許容されない。
    // setAttr は不要なので、入力と違い NumericData の列挙までは不要とする。
    fnGeneric.addDataAccept(MFnData::kAny);
    //fnGeneric.addDataAccept(MFnData::kNumeric);
    //fnGeneric.addNumericDataAccept(MFnNumericData::k2Short);
    //fnGeneric.addNumericDataAccept(MFnNumericData::k3Short);
    //fnGeneric.addNumericDataAccept(MFnNumericData::k2Long);
    //fnGeneric.addNumericDataAccept(MFnNumericData::k3Long);
    //fnGeneric.addNumericDataAccept(MFnNumericData::k2Float);
    //fnGeneric.addNumericDataAccept(MFnNumericData::k3Float);
    //fnGeneric.addNumericDataAccept(MFnNumericData::k2Double);
    //fnGeneric.addNumericDataAccept(MFnNumericData::k3Double);
    //fnGeneric.addNumericDataAccept(MFnNumericData::k4Double);
    fnGeneric.addDataAccept(MFnData::kPlugin);
    fnGeneric.addDataAccept(MFnData::kPluginGeometry);
    fnGeneric.addDataAccept(MFnData::kString);
    fnGeneric.addDataAccept(MFnData::kMatrix);
    fnGeneric.addDataAccept(MFnData::kStringArray);
    fnGeneric.addDataAccept(MFnData::kDoubleArray);
    fnGeneric.addDataAccept(MFnData::kIntArray);
    fnGeneric.addDataAccept(MFnData::kPointArray);
    fnGeneric.addDataAccept(MFnData::kVectorArray);
    fnGeneric.addDataAccept(MFnData::kComponentList);
    fnGeneric.addDataAccept(MFnData::kMesh);
    fnGeneric.addDataAccept(MFnData::kLattice);
    fnGeneric.addDataAccept(MFnData::kNurbsCurve);
    fnGeneric.addDataAccept(MFnData::kNurbsSurface);
    fnGeneric.addDataAccept(MFnData::kSphere);
    fnGeneric.addDataAccept(MFnData::kDynArrayAttrs);
    fnGeneric.addDataAccept(MFnData::kSubdSurface);
    // 以下は input と違ってクラッシュはしないようだが不要だろう。
    //fnGeneric.addDataAccept(MFnData::kDynSweptGeometry);
    //fnGeneric.addDataAccept(MFnData::kNObject);
    //fnGeneric.addDataAccept(MFnData::kNId);

    fnGeneric.setWritable(false);
    fnGeneric.setStorable(false);
    fnGeneric.setArray(true);
    fnGeneric.setDisconnectBehavior(MFnAttribute::kDelete);
    CHECK_MSTATUS_AND_RETURN_IT(addAttribute(aOutput));

    // Set the attribute dependencies.
    attributeAffects(aCode, aCompiled);
    attributeAffects(aCode, aOutput);
    attributeAffects(aInputsAsApi1Object, aOutput);
    attributeAffects(aInput, aOutput);

    return MS::kSuccess;
}


//------------------------------------------------------------------------------
/// Constructor.
//------------------------------------------------------------------------------
Exprespy::Exprespy() :
    _base_globals(NULL),
    _input(NULL),
    _output(NULL),
    _globals(NULL),
    _codeobj(NULL),
    _mplug2_input(NULL),
    _mplug2_output(NULL),
    _mplug1_input(NULL),
    _mplug1_output(NULL),

    _api2_dict(NULL),
    _type2_MVector(NULL),
    _type2_MPoint(NULL),
    _type2_MEulerRotation(NULL),
    _type2_MMatrix(NULL),
    _type2_MObject(NULL),
    _type2_MQuaternion(NULL),
    _type2_MColor(NULL),
    _type2_MFloatVector(NULL),
    _type2_MFloatPoint(NULL),

    _api1_dict(NULL),
    _type1_MObject(NULL),

    _type_StringIO(NULL),
    _sys_dict(NULL),
    _sys_stdout(NULL),
    _sys_stderr(NULL),

    _count(0)
{
}


//------------------------------------------------------------------------------
/// Destructor.
//------------------------------------------------------------------------------
Exprespy::~Exprespy()
{
    if (_base_globals) {
        PyGILState_STATE gil = PyGILState_Ensure();

        Py_XDECREF(_sys_stdout);
        Py_XDECREF(_sys_stderr);

        Py_XDECREF(_mplug2_input);
        Py_XDECREF(_mplug2_output);
        Py_XDECREF(_mplug1_input);
        Py_XDECREF(_mplug1_output);

        Py_XDECREF(_codeobj);
        Py_XDECREF(_globals);

        Py_DECREF(_output);
        Py_DECREF(_input);
        Py_DECREF(_base_globals);

        PyGILState_Release(gil);
    }
}


//------------------------------------------------------------------------------
/// Computation.
//------------------------------------------------------------------------------
MStatus Exprespy::compute(const MPlug& plug, MDataBlock& block)
{
    if (plug == aCompiled) {
        return _compileCode(block);
    } else if (plug == aOutput) {
        return _executeCode(block);
    }
    return MS::kUnknownParameter;
}


//------------------------------------------------------------------------------
/// Compile a code.
//------------------------------------------------------------------------------
MStatus Exprespy::_compileCode(MDataBlock& block)
{
    MString code = block.inputValue(aCode).asString();

    //MGlobal::displayInfo("COMPILE");

    // Python の処理開始（GIL取得）。
    PyGILState_STATE gil = PyGILState_Ensure();

    // 一度構築済みなら古いコンパイル済みコードを破棄。
    if (_base_globals) {
        Py_CLEAR(_codeobj);
        Py_CLEAR(_globals);

    // 初めてなら環境構築する。
    } else {
        PyObject* builtins = PyImport_ImportModule(BUILTINS_MODULE_NAME);
        if (builtins) {
            // ローカル環境 (globals) のベースを構築する。
            // これは書き換えられないように保持し、各コード向けにはこれを複製して利用する。
            _base_globals = PyDict_New();
            _input = PyDict_New();
            _output = PyDict_New();

            if (_base_globals && _input && _output) {
                // 組み込み辞書をセット。
                _setDictStealValue(_base_globals, "__builtins__", builtins);
                _setDictStealValue(_base_globals, "__name__", PYSTR_fromChar("__exprespy__"));

                // ノードの入出力のための dict を生成。
                PyDict_SetItemString(_base_globals, "IN", _input);
                PyDict_SetItemString(_base_globals, "OUT", _output);

                // モジュールをインポートし globals にセット。
                PyObject* mod_api2 = _importModule("maya.api.OpenMaya");
                _setDictStealValue(_base_globals, "api", mod_api2);
                _setDictStealValue(_base_globals, "math", _importModule("math"));
                _setDictStealValue(_base_globals, "cmds", _importModule("maya.cmds"));
                _setDictStealValue(_base_globals, "mel", _importModule("maya.mel"));
                PyObject* mod_api1 = _importModule("maya.OpenMaya");
                _setDictStealValue(_base_globals, "api1", mod_api1);
                PyObject* mod_sys = _importModule("sys");
                _setDictStealValue(_base_globals, "sys", mod_sys);

                // Python API からクラスを取得しておく。「無くならない前提」で INCREF せずに保持する。
                // NOTE: 無くなることも有り得る（例えば、参照を破棄してインポートし直し）と考えると少々危険ではある。
                if (mod_api2) {
                    _api2_dict = PyModule_GetDict(mod_api2);
                    _type2_MVector = _getTypeObject(_api2_dict, "MVector");
                    _type2_MPoint = _getTypeObject(_api2_dict, "MPoint");
                    _type2_MEulerRotation = _getTypeObject(_api2_dict, "MEulerRotation");
                    _type2_MMatrix = _getTypeObject(_api2_dict, "MMatrix");
                    _type2_MObject = _getTypeObject(_api2_dict, "MObject");
                    _type2_MQuaternion = _getTypeObject(_api2_dict, "MQuaternion");
                    _type2_MColor = _getTypeObject(_api2_dict, "MColor");
                    _type2_MFloatVector = _getTypeObject(_api2_dict, "MFloatVector");
                    _type2_MFloatPoint = _getTypeObject(_api2_dict, "MFloatPoint");
                }
                if (mod_api1) {
                    _api1_dict = PyModule_GetDict(mod_api1);
                    _type1_MObject = _getTypeObject(_api1_dict, "MObject");
                }

                // 出力ストリームを乗っ取るための準備。
                if (mod_sys) {
                    PyObject* mod_StringIO = _importModule(STRINGIO_MODULE);
                    if (mod_StringIO) {
                        _type_StringIO = PyDict_GetItemString(PyModule_GetDict(mod_StringIO), "StringIO");
                        if (_type_StringIO) {
                            // stdout と stdin は INCREF しておかないと、乗っ取った時にクラッシュしたりする。
                            _sys_dict = PyModule_GetDict(mod_sys);
                            _sys_stdout = PyDict_GetItemString(_sys_dict, "stdout");
                            if (_sys_stdout) Py_INCREF(_sys_stdout);
                            _sys_stderr = PyDict_GetItemString(_sys_dict, "stderr");
                            if (_sys_stderr) Py_INCREF(_sys_stderr);
                        }
                    }
                }

            } else {
                // 環境構築に失敗。
                Py_CLEAR(_base_globals);
                Py_CLEAR(_input);
                Py_CLEAR(_output);
            }
        }
    }

    // ローカル環境の複製と、ソースコードのコンパイル。
    if (_base_globals) {
        _globals = PyDict_Copy(_base_globals);
        if (_globals) {
            _codeobj = reinterpret_cast<PyCodeObject*>(Py_CompileString(code.asChar(), "exprespy_code", Py_file_input));
            if(PyErr_Occurred()){
                //MGlobal::displayInfo("Compile: error!");
                Py_CLEAR(_codeobj);
                _printPythonError();
            }
        }
        _count = 0;
    }

    // Python の処理終了（GIL解放）。
    PyGILState_Release(gil);

    // コンパイルの成否をセット。
    //MGlobal::displayInfo(_codeobj ? "successfull" : "failed");
    block.outputValue(aCompiled).set(_codeobj ? true : false);
    return MS::kSuccess;
}


//------------------------------------------------------------------------------
/// Execute a code.
//------------------------------------------------------------------------------
MStatus Exprespy::_executeCode(MDataBlock& block)
{
    block.inputValue(aCompiled);

    MArrayDataHandle hArrOutput = block.outputArrayValue(aOutput);

    if (_codeobj) {
        //MGlobal::displayInfo("EXECUTE");

        // GIL取得前に上流評価を終える。
        const bool inputsAsApi1Object = block.inputValue(aInputsAsApi1Object).asBool();
        MArrayDataHandle hArrInput = block.inputArrayValue(aInput);
        // この段階で上流が評価され終わっている。

        // Python の処理開始（GIL取得）。
        PyGILState_STATE gil = PyGILState_Ensure();

        // .input[i] から値を得て IN[i] にセットする。
        if (hArrInput.elementCount()) {
            do {
                const unsigned idx = hArrInput.elementIndex();

                MDataHandle hInput = hArrInput.inputValue();
                if (hInput.type() == MFnData::kNumeric) {
                    // generic では、残念ながら数値型の詳細は判別できない。
                    _setInputScalar(idx, hInput.asGenericDouble());
                } else {
                    MObject data = hInput.data();
                    switch (data.apiType()) {
                    case MFn::kMatrixData:  // matrix --> MMatrix (API2)
                        _setInputMatrix(idx, data);
                        break;
                    case MFn::kStringData:  // string --> unicode
                        _setInputString(idx, hInput.asString());
                        break;
                    case MFn::kData2Short:  // short2 --> list
                        _setInputShort2(idx, data);
                        break;
                    case MFn::kData3Short:  // short3 --> list
                        _setInputShort3(idx, data);
                        break;
                    case MFn::kData2Long:  // long2 --> list
                        _setInputLong2(idx, data);
                        break;
                    case MFn::kData3Long:  // long3 --> list
                        _setInputLong3(idx, data);
                        break;
                    case MFn::kData2Float:  // float2 --> list
                        _setInputFloat2(idx, data);
                        break;
                    case MFn::kData3Float:  // float3 --> list
                        _setInputFloat3(idx, data);
                        break;
                    case MFn::kData2Double:  // double2 --> list
                        _setInputDouble2(idx, data);
                        break;
                    case MFn::kData3Double:  // double3 --> MVector (API2)
                        _setInputVector3(idx, data);
                        break;
                    case MFn::kData4Double:  // double4 --> list
                        // NOTE:
                        //   transform.rotateQuaternion は double4 だが、quatNodes の quaternion は double4 ではなく compound である。
                        //   double4 とそれ相当の compound 同士を接続する分には問題なく値のやりとりがされる。
                        //   generic の出力でも double4 データを作って出していれば double4 でも compound でも受け取れるようだ。
                        //
                        //   compound の場合の generic の入力が問題となる。
                        //   それは hInput.type() == kInvalid && data.apiType() == kInvalid となり、
                        //   ここには来ずに default の方に行き、値を得ることができず None となる。
                        //   タイプ判別ができないだけでなく、本当に得られない。
                        //   MFnNumericData() で無理やり得ようとしてもダメだし、2019 から追加された asDouble4() でも得られない。
                        //   ちなみに、generic だからか asDouble4() では MFn::kData4Double の場合でも得られないようだ。
                        _setInputDouble4(idx, data);
                        break;
                    default:                 // other data --> MObject (API2 or 1)
                        //MGlobal::displayInfo(data.apiTypeStr());
                        if (! data.hasFn(MFn::kData)) {
                            // 接続の undo 時などに kInvalid が来る。isNull() でも判定出来たが、一応 data だけ通すようにする。
                            _setDictValue(_input, idx, Py_None);
                        } else if (inputsAsApi1Object) {
                            _setInputMObject1(idx);
                        } else {
                            _setInputMObject2(idx);
                        }
                    }
                }
            } while (hArrInput.next());
        }

        // カウンターをセット。
        _setDictStealValue(_globals, "COUNT", PYINT_fromLong(_count));
        ++_count;

        // sys.stdout を StringIO で奪う。
        // 何故か print の出力行が逆転することがあるので、バッファに溜めて一回で write するようにする。
        // python の print も MGloba::displayInfo も Maya に制御が返されない限り flush されないので、その点は変わらない。
        // なお、この逆転現象は起きたり起きなかったりし、条件はよく分からない。Maya 2017 win64 でいくらか試すと簡単に再現出来た。
        PyObject* stream = NULL;
        if (_sys_stdout && _type_StringIO) {
            stream = PyObject_CallObject(_type_StringIO, NULL);
            if (stream) {
                PyDict_SetItemString(_sys_dict, "stdout", stream);
            }
        }

        // コンパイル済みコードオブジェクトを実行。
#if PY_MAJOR_VERSION < 3
        PyEval_EvalCode(_codeobj, _globals, NULL);
#else
        PyEval_EvalCode(reinterpret_cast<PyObject*>(_codeobj), _globals, NULL);
#endif
        if(PyErr_Occurred()){
            //MGlobal::displayInfo("PyEval_EvalCode: error!");
            _printPythonError();
        }

        // NOTE: py3 ではエラーインジケータをクリアする前に open 済み StringIO を使用するとクラッシュするので注意!!

        // StringIO の中身を本当の sys.stdout に書き出し、sys.stdout を元に戻す。
        // MGlobal::displayInfo を用いないのは、コメント化をさせずにダイレクトに print させるため。
        if (stream) {
            PyObject* str = PyObject_CallMethod(stream, "getvalue", NULL);
            if (str) {
#if PY_MAJOR_VERSION < 3
                if ((PyUnicode_Check(str) && PyUnicode_GET_SIZE(str)) || PYBYTES_SIZE(str))
#else
                if (PyUnicode_GET_SIZE(str))
#endif
                    PyObject_CallMethod(_sys_stdout, "write", "(O)", str);
                Py_DECREF(str);
            }

            PyDict_SetItemString(_sys_dict, "stdout", _sys_stdout);
            PyObject_CallMethod(stream, "close", NULL);
            Py_DECREF(stream);
        }

        // .output[i] に OUT[i] の値をセットする。存在しないものや扱えないもの場合は無視する。
        if (hArrOutput.elementCount()) {
            MMatrix mat;
            do {
                const unsigned idx = hArrOutput.elementIndex();

                PyObject* valo = _getDictValue(_output, idx);  // 保持しないので INCREF しない。
                if (! valo) continue;

                // float --> double
                if (PyFloat_Check(valo)) {
                    hArrOutput.outputValue().setGenericDouble(PyFloat_AS_DOUBLE(valo), true);

#if PY_MAJOR_VERSION < 3
                // int --> int
                } else if (PyInt_Check(valo)) {
                    hArrOutput.outputValue().setGenericInt(PyInt_AS_LONG(valo), true);
#endif

                // long int --> int
                } else if (PyLong_Check(valo)) {
                    hArrOutput.outputValue().setGenericInt(PyLong_AsLong(valo), true);  // TODO: OverflowError 対策。

                // bool --> bool
                } else if (PyBool_Check(valo)) {
                    hArrOutput.outputValue().setGenericBool(valo == Py_True, true);

                // str(bytes) --> string
                } else if (PYBYTES_check(valo)) {
                    hArrOutput.outputValue().set(MString(PYBYTES_asChar(valo)));

                // unicode(str) --> string
                } else if (PyUnicode_Check(valo)) {
                    // これだと py3 だと結果がおかしく、py2 でもコードのエンコードタイプに依存することになる。
                    // アトリビュートは、OSと言語ごとに定められたMayaシーンのエンコードタイプが正しい。
                    // Linux or Mac: utf-8, Windows日本語=cp932(SJIS), Windows簡体中国語=cp936(GBK)
                    //PyObject* es = PyUnicode_AsEncodedString(valo, Py_FileSystemDefaultEncoding, NULL);
                    //if (es) {
                    //    hArrOutput.outputValue().set(MString(PYBYTES_asChar(es)));
                    //    Py_DECREF(es);
                    //}

                    // wchar_t のまま MString 化するが 3.2 未満だと API が古いので切り分ける。
#if PY_MAJOR_VERSION < 3 || (PY_MAJOR_VERSION == 3 && PY_MINOR_VERSION < 2)
                    wchar_t* ws = 0;
                    Py_ssize_t siz = PyUnicode_GET_SIZE(valo);
                    if (siz) {
                        ++siz;
                        ws = reinterpret_cast<wchar_t*>(PyMem_Malloc(siz * sizeof(wchar_t)));
                    }
                    if (ws) {
                        PyUnicode_AsWideChar(reinterpret_cast<PyUnicodeObject*>(valo), ws, siz);
#else
                    wchar_t* ws = PyUnicode_AsWideCharString(valo, NULL);
                    if (ws) {
#endif
                        hArrOutput.outputValue().set(MString(ws));
                        PyMem_Free(ws);
                    }
                    else
                        hArrOutput.outputValue().set(MString());

                // MMatrix (API2) --> matrix
                } else if (_type2_MMatrix && PyObject_IsInstance(valo, _type2_MMatrix)) {
                    _getMatrixValueFromPyObject(mat, valo);
                    hArrOutput.outputValue().set(MFnMatrixData().create(mat));

                // MVector, MPoint, MEulerRotation (API2) --> double3
                } else if ((_type2_MVector && PyObject_IsInstance(valo, _type2_MVector))
                 || (_type2_MPoint && PyObject_IsInstance(valo, _type2_MPoint))
                 || (_type2_MEulerRotation && PyObject_IsInstance(valo, _type2_MEulerRotation))) {
                    hArrOutput.outputValue().set(_getDouble3Value(valo));

                // MQuaternion (API2) --> double4
                } else if (_type2_MQuaternion && PyObject_IsInstance(valo, _type2_MQuaternion)) {
                    hArrOutput.outputValue().set(_getDouble4Value(valo));

                // MFloatVector, MFloatPoint, MColor (API2) --> float3
                } else if ((_type2_MFloatVector && PyObject_IsInstance(valo, _type2_MFloatVector))
                 || (_type2_MFloatPoint && PyObject_IsInstance(valo, _type2_MFloatPoint))
                 || (_type2_MColor && PyObject_IsInstance(valo, _type2_MColor))) {
                    hArrOutput.outputValue().set(_getFloat3Value(valo));

                // sequence --> double2, double3, double4, long2, long3, or null
                } else if (PySequence_Check(valo)) {
                    hArrOutput.outputValue().set(_getTypedSequence(valo));

                // MObject (API2 or 1) --> data
                } else if (_type2_MObject && PyObject_IsInstance(valo, _type2_MObject)) {
                    _setOutputMObject2(idx, valo);
                } else if (_type1_MObject && PyObject_IsInstance(valo, _type1_MObject)) {
                    _setOutputMObject1(idx, valo);
                }
            } while (hArrOutput.next());
        }

        // 次回のために IN と OUT をクリアしておく。
        PyDict_Clear(_input);
        PyDict_Clear(_output);

        // Python の処理終了（GIL解放）。
        PyGILState_Release(gil);
    }

    return hArrOutput.setAllClean();
}


//------------------------------------------------------------------------------
/// Python のエラーを Maya のエラーメッセージとして出力する。
/// メッセージを赤くする共に、何故か行の順序が逆転する場合があるのを回避する。
//------------------------------------------------------------------------------
#if PY_MAJOR_VERSION < 3
void Exprespy::_printPythonError()
{
    // 当然ながら、コンパイルエラーでは traceback オブジェクトは得られず、ランタイムエラーでは得られる。
    //PyObject *errtyp, *errval, *tb;
    //PyErr_Fetch(&errtyp, &errval, &tb);
    //MGlobal::displayInfo(
    //    MString("errtyp=") + (errtyp ? "1" : "0")
    //    + ", errval="  + (errval ? "1" : "0")
    //    + ", tb="  + (tb ? "1" : "0")
    //);
    //PyErr_Restore(errtyp, errval, tb);

    // sys.stderr を StringIO で奪う。
    PyObject* stream = NULL;
    if (_sys_stderr && _type_StringIO) {
        stream = PyObject_CallObject(_type_StringIO, NULL);
        if (stream) {
            PyDict_SetItemString(_sys_dict, "stderr", stream);
        }
    }

    // 現在のエラー情報を stderr に書き出す。
    PyErr_Print();

    // StringIO の中身を本当の sys.stderr に書き出し、sys.stderr を元に戻す。
    if (stream) {
        PyObject* str = PyObject_CallMethod(stream, "getvalue", NULL);
        if (str) {
            if (PYBYTES_SIZE(str)) {
                MGlobal::displayError(PYBYTES_asChar(str));
            }
            Py_DECREF(str);
        }
        PyDict_SetItemString(_sys_dict, "stderr", _sys_stderr);
        PyObject_CallMethod(stream, "close", NULL);
        Py_DECREF(stream);
    }
}

//------------------------------------------------------------------------------
#else
void Exprespy::_printPythonError()
{
    // py3 では、traceback オブジェクトはコンパイルエラーでもランタイムエラーでも得られない。
    // StringIO を生成しようとすると SystemError: <class '_io.StringIO'> returned a result with an error set となる。
    // traceback.format_exc() でもエラーテキストを得られない。
    // どうしてよいか分からないので PyErr_Print を直接呼ぶのみとし、その後の displayError で赤くする。
    PyErr_Print();
    MGlobal::displayError("An error has occured.");

#if 0
#if 0
    PyObject *errtyp, *errval, *tb;
    PyErr_Fetch(&errtyp, &errval, &tb);
    MGlobal::displayInfo(
        MString("errtyp=") + (errtyp ? "1" : "0")
        + ", errval="  + (errval ? "1" : "0")
        + ", tb="  + (tb ? "1" : "0")
    );
    if (! tb) {
        PyErr_Restore(errtyp, errval, tb);
        PyErr_Print();
        return;
    }
#endif

    MGlobal::displayInfo("import traceback");
    PyObject* mod_traceback = PyImport_ImportModule("traceback");
    if (mod_traceback) {
#if 0
        MGlobal::displayInfo("get format_tb");
        PyObject* format_tb = PyDict_GetItemString(PyModule_GetDict(mod_traceback), "format_tb");  // borrow
        MGlobal::displayInfo(MString("format_tb=") + (format_tb ? "1" : "0"));
        PyObject* str = PyObject_CallFunction(format_tb, "(O)", tb);
#else
        MGlobal::displayInfo("get format_exc");
        PyObject* format_exc = PyDict_GetItemString(PyModule_GetDict(mod_traceback), "format_exc");  // borrow
        MGlobal::displayInfo(MString("format_exc=") + (format_exc ? "1" : "0"));
        PyObject* str = PyObject_CallObject(format_exc, NULL);
#endif
        MGlobal::displayInfo(MString("str=") + (str ? "1" : "0"));
        if (str) {
            MGlobal::displayInfo("asUTF8");
            PyObject* bs = PyUnicode_AsUTF8String(str);
            MString mstr;
            mstr.setUTF8(PYBYTES_asChar(bs));
            MGlobal::displayError(mstr);
            Py_DECREF(bs);

            Py_DECREF(str);
        }

        Py_DECREF(mod_traceback);
    }

    //Py_DECREF(errtyp);
    //Py_DECREF(errval);
    //Py_DECREF(tb);
#endif
}
#endif


//------------------------------------------------------------------------------
/// _input dict にスカラー数値をセットする。
//------------------------------------------------------------------------------
void Exprespy::_setInputScalar(int key, const double& val)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        // 入力から型判別出来ないため、せめて整数と実数を判別する。
        int i = static_cast<int>(val);
        if (static_cast<double>(i) == val) {
            _setIODictStealValue(_input, keyo, PYINT_fromLong(i));
        } else {
            _setIODictStealValue(_input, keyo, PyFloat_FromDouble(val));
        }
    }
}


//------------------------------------------------------------------------------
/// _input dict に文字列をセットする。
//------------------------------------------------------------------------------
void Exprespy::_setInputString(int key, const MString& str)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        _setIODictStealValue(_input, keyo, PyUnicode_FromString(str.asUTF8()));
    }
}


//------------------------------------------------------------------------------
/// _input dict に要素が 2～4 個の値を list にしてセットする。
//------------------------------------------------------------------------------
void Exprespy::_setInputShort2(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        short x, y;
        MFnNumericData(data).getData(x, y);
        _setIODictStealValue(_input, keyo, Py_BuildValue("[hh]", x, y));
    }
}

void Exprespy::_setInputShort3(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        short x, y, z;
        MFnNumericData(data).getData(x, y, z);
        _setIODictStealValue(_input, keyo, Py_BuildValue("[hhh]", x, y, z));
    }
}

void Exprespy::_setInputLong2(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        int x, y;
        MFnNumericData(data).getData(x, y);
        _setIODictStealValue(_input, keyo, Py_BuildValue("[ii]", x, y));
    }
}

void Exprespy::_setInputLong3(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        int x, y, z;
        MFnNumericData(data).getData(x, y, z);
        _setIODictStealValue(_input, keyo, Py_BuildValue("[iii]", x, y, z));
    }
}

void Exprespy::_setInputFloat2(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        float x, y;
        MFnNumericData(data).getData(x, y);
        _setIODictStealValue(_input, keyo, Py_BuildValue("[ff]", x, y));
    }
}

void Exprespy::_setInputFloat3(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        float x, y, z;
        MFnNumericData(data).getData(x, y, z);
        _setIODictStealValue(_input, keyo, Py_BuildValue("[fff]", x, y, z));
    }
}

void Exprespy::_setInputDouble2(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        double x, y;
        MFnNumericData(data).getData(x, y);
        _setIODictStealValue(_input, keyo, Py_BuildValue("[dd]", x, y));
    }
}

void Exprespy::_setInputDouble3(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        double x, y, z;
        MFnNumericData(data).getData(x, y, z);
        _setIODictStealValue(_input, keyo, Py_BuildValue("[ddd]", x, y, z));
    }
}

void Exprespy::_setInputDouble4(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        double x, y, z, w;
        MFnNumericData(data).getData(x, y, z, w);
        _setIODictStealValue(_input, keyo, Py_BuildValue("[dddd]", x, y, z, w));
    }
}


//------------------------------------------------------------------------------
/// _input dict に double3 を MVector か list にしてセットする。
//------------------------------------------------------------------------------
void Exprespy::_setInputVector3(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        double x, y, z;
        MFnNumericData(data).getData(x, y, z);
        if (_type2_MVector) {
            _setIODictStealValue(_input, keyo, PyObject_CallFunction(_type2_MVector, "(ddd)", x, y, z));
        } else {
            _setIODictStealValue(_input, keyo, Py_BuildValue("[ddd]", x, y, z));
        }
    }
}


//------------------------------------------------------------------------------
/// _input dict に matrix を MMatrix か list にしてセットする。
//------------------------------------------------------------------------------
void Exprespy::_setInputMatrix(int key, MObject& data)
{
    PyObject* keyo = PYINT_fromLong(key);
    if (keyo) {
        MMatrix m = MFnMatrixData(data).matrix();
        if (_type2_MMatrix) {
            _setIODictStealValue(_input, keyo, PyObject_CallFunction(_type2_MMatrix, "(N)", Py_BuildValue(
                "(dddddddddddddddd)",
                m.matrix[0][0], m.matrix[0][1], m.matrix[0][2], m.matrix[0][3],
                m.matrix[1][0], m.matrix[1][1], m.matrix[1][2], m.matrix[1][3],
                m.matrix[2][0], m.matrix[2][1], m.matrix[2][2], m.matrix[2][3],
                m.matrix[3][0], m.matrix[3][1], m.matrix[3][2], m.matrix[3][3]
            )));
        } else {
            _setIODictStealValue(_input, keyo, Py_BuildValue(
                "[dddddddddddddddd]",
                m.matrix[0][0], m.matrix[0][1], m.matrix[0][2], m.matrix[0][3],
                m.matrix[1][0], m.matrix[1][1], m.matrix[1][2], m.matrix[1][3],
                m.matrix[2][0], m.matrix[2][1], m.matrix[2][2], m.matrix[2][3],
                m.matrix[3][0], m.matrix[3][1], m.matrix[3][2], m.matrix[3][3]
            ));
        }
    }
}


//------------------------------------------------------------------------------
/// _input dict に Python API 2 MObject データをセットする。
/// MObjet を C++ から Python に変換する手段が無いので、不本意ながら MPlug を利用。
//------------------------------------------------------------------------------
void Exprespy::_setInputMObject2(int key)
{
    _preparePyPlug2();
    if (! _mplug2_input) return;

    PyObject* keyo = PYINT_fromLong(key);
    if (! keyo) return;

    PyObject* mplug = PyObject_CallMethod(_mplug2_input, "elementByLogicalIndex", "(O)", keyo);
    if (mplug) {
        _setIODictStealValue(_input, keyo, PyObject_CallMethod(mplug, "asMObject", NULL));
        Py_DECREF(mplug);
    } else {
        Py_DECREF(keyo);
    }
}


//------------------------------------------------------------------------------
/// _output dict から得た Python API 2 MObject データを出力プラグにセットする。
/// MObjet を Python から C++ に変換する手段が無いので、不本意ながら MPlug を利用。
//------------------------------------------------------------------------------
void Exprespy::_setOutputMObject2(int key, PyObject* valo)
{
    _preparePyPlug2();
    if (! _mplug2_output) return;

    PyObject* mplug = PyObject_CallMethod(_mplug2_output, "elementByLogicalIndex", "(i)", key);
    if (mplug) {
        PyObject_CallMethod(mplug, "setMObject", "(O)", valo);
        Py_DECREF(mplug);
    }
}


//------------------------------------------------------------------------------
/// MObject データ入出力のための Python API 2 MPlug を取得しておく。
//------------------------------------------------------------------------------
void Exprespy::_preparePyPlug2()
{
    if (_mplug2_input || ! _api2_dict) return;

    PyObject* pysel = PyObject_CallObject(PyDict_GetItemString(_api2_dict, "MSelectionList"), NULL);
    if (! pysel) return;

    MString nodename = MFnDependencyNode(thisMObject()).name();
    PyObject_CallMethod(pysel, "add", "(s)", nodename.asChar());
    PyObject* pynode = PyObject_CallMethod(pysel, "getDependNode", "(i)", 0);
    Py_DECREF(pysel);
    if (! pynode) return;

    PyObject* pyfn = PyObject_CallFunction(PyDict_GetItemString(_api2_dict, "MFnDependencyNode"), "(O)", pynode);
    Py_DECREF(pynode);
    if (! pyfn) return;

    PyObject* findPlug = PyObject_GetAttrString(pyfn, "findPlug");  // DECREF 不要。
    _mplug2_input = PyObject_CallFunction(findPlug, "(sO)", "i", Py_False);
    _mplug2_output = PyObject_CallFunction(findPlug, "(sO)", "o", Py_False);
    Py_DECREF(pyfn);
}


//------------------------------------------------------------------------------
/// _input dict に Python API 1 MObject データをセットする。
/// MObjet を C++ から Python に変換する手段が無いので、不本意ながら MPlug を利用。
//------------------------------------------------------------------------------
void Exprespy::_setInputMObject1(int key)
{
    _preparePyPlug1();
    if (! _mplug1_input) return;

    PyObject* keyo = PYINT_fromLong(key);
    if (! keyo) return;

    PyObject* mplug = PyObject_CallMethod(_mplug1_input, "elementByLogicalIndex", "(O)", keyo);
    if (! mplug) { Py_DECREF(keyo); return; }

    PyObject* valo = PyObject_CallMethod(mplug, "asMObject", NULL);
    Py_DECREF(mplug);

    _setIODictStealValue(_input, keyo, valo);
}


//------------------------------------------------------------------------------
/// _output dict から得た Python API 1 MObject データを出力プラグにセットする。
/// MObjet を Python から C++ に変換する手段が無いので、不本意ながら MPlug を利用。
//------------------------------------------------------------------------------
void Exprespy::_setOutputMObject1(int key, PyObject* valo)
{
    _preparePyPlug1();
    if (! _mplug1_output) return;

    PyObject* mplug = PyObject_CallMethod(_mplug1_output, "elementByLogicalIndex", "(i)", key);
    if (mplug) {
        PyObject_CallMethod(mplug, "setMObject", "(O)", valo);
        Py_DECREF(mplug);
    }
}


//------------------------------------------------------------------------------
/// MObject データ入出力のための Python API 1 MPlug を取得しておく。
//------------------------------------------------------------------------------
void Exprespy::_preparePyPlug1()
{
    if (_mplug1_input || ! _api1_dict) return;

    PyObject* pysel = PyObject_CallObject(PyDict_GetItemString(_api1_dict, "MSelectionList"), NULL);
    if (! pysel) return;

    MString nodename = MFnDependencyNode(thisMObject()).name();
    PyObject_CallMethod(pysel, "add", "(s)", nodename.asChar());
    PyObject* pynode = PyObject_CallObject(_type1_MObject, NULL);
    if (! pynode) return;
    PyObject_CallMethod(pysel, "getDependNode", "(iO)", 0, pynode);
    Py_DECREF(pysel);

    if (PyObject_CallMethod(pynode, "isNull", NULL) != Py_True) {
        PyObject* pyfn = PyObject_CallFunction(PyDict_GetItemString(_api1_dict, "MFnDependencyNode"), "(O)", pynode);

        PyObject* findPlug = PyObject_GetAttrString(pyfn, "findPlug");  // DECREF 不要。
        if (findPlug) {
            _mplug1_input = PyObject_CallFunction(findPlug, "(sO)", "i", Py_False);
            _mplug1_output = PyObject_CallFunction(findPlug, "(sO)", "o", Py_False);
            if (PyObject_CallMethod(_mplug1_input, "isNull", NULL) == Py_True) Py_CLEAR(_mplug1_input);
            if (PyObject_CallMethod(_mplug1_output, "isNull", NULL) == Py_True) Py_CLEAR(_mplug1_output);
        }

        Py_DECREF(pyfn);
    }
    Py_DECREF(pynode);
}


//=============================================================================
//  ENTRY POINT FUNCTIONS
//=============================================================================
MStatus initializePlugin(MObject obj)
{ 
    static const char* VERSION = "3.0.1.20220627";
    static const char* VENDER  = "Ryusuke Sasaki";

    MFnPlugin plugin(obj, VENDER, VERSION, "Any");

    MStatus stat = plugin.registerNode(Exprespy::name, Exprespy::id, Exprespy::creator, Exprespy::initialize);
    CHECK_MSTATUS_AND_RETURN_IT(stat);

    return MS::kSuccess;
}

MStatus uninitializePlugin(MObject obj)
{
    MStatus stat = MFnPlugin(obj).deregisterNode(Exprespy::id);
    CHECK_MSTATUS_AND_RETURN_IT(stat);

    return MS::kSuccess;
}

