# -*- coding: utf-8 -*-
u"""
Support module for exprespy plug-in.
"""
from __future__ import absolute_import
from __future__ import print_function

import sys
import re
import maya.cmds as cmds
if sys.hexversion < 0x3000000:
    from itertools import izip_longest as zip_longest
else:
    from itertools import zip_longest
import maya.api.OpenMaya as _api2

__all__ = ['create', 'setCode', 'getCode']

_2_getAPathTo = _api2.MDagPath.getAPathTo
_2_MFnDependencyNode = _api2.MFnDependencyNode
_2_MSelectionList = _api2.MSelectionList


#------------------------------------------------------------------------------
def create(code='', raw=False):
    u"""
    exprespy ノードを新規生成し、コード文字列をセットする。
    """
    cmds.loadPlugin('exprespy', qt=True)
    node = cmds.createNode('exprespy')
    setCode(node, code, raw=raw)
    return node


def setCode(node, code, raw=False):
    u"""
    exprespy ノードにコード文字列をセットする。
    """
    if raw:
        cmds.setAttr(node + '.cd', code, type='string')
        return

    # 既存の入出力プラグ辞書を得る。
    mfn = _2_MFnDependencyNode(_get_mnode(node))
    keepIn = _getInputDict(mfn, all=True)
    keepOut = _getOutputDict(mfn)

    # 既存のコードをチェックし、管理している入出力（編集対象）とそれ以外（維持対象）とに分離する。
    rawcode = cmds.getAttr(node + '.cd') or ''
    newcode, newIn, removeIn, newOut, oldOut = _toRawCode(code, rawcode, keepIn, keepOut)

    #_printPlugChange('IN', newIn, keepIn, removeIn)
    #_printPlugChange('OUT', newOut, keepOut, oldOut)

    # コネクション変更とコード文字列のセット。
    outUpdated = _updateOutputs(node, newOut, oldOut, keepOut)
    if newcode == rawcode:
        # コード文字列もコネクションにも変更が無ければ、文字列だけセット。
        if not(_updateInputs(node, newIn, removeIn) or outUpdated or newOut):
            cmds.setAttr(node + '.cd', newcode, type='string')
    else:
        # エラー抑止のためコードを除去してから入力を変更。
        cmds.setAttr(node + '.cd', '', type='string')
        _updateInputs(node, newIn, removeIn)
        cmds.setAttr(node + '.cd', newcode, type='string')
    if newOut:
        _connectOutputs(node, newOut)


def getCode(node, raw=False, short=False):
    u"""
    exprespy ノードからコード文字列を得る。
    """
    code = cmds.getAttr(node + '.cd') or ''
    if raw:
        return code
    mfn = _2_MFnDependencyNode(_get_mnode(node))
    return _toHumanCode(code, _getInputDict(mfn, short), _getOutputDict(mfn, short))


#------------------------------------------------------------------------------
_RE_PLUG = re.compile(r'([\|\:]?[a-zA-Z_]\w*(?:[\|\:][a-zA-Z_]\w*)*(?:\.[a-zA-Z_]\w*(?:\[\d+\])?)+)(\s*\=)?')
_RE_IO_PLUG = re.compile(r'(IN|OUT)\[(\d+)\]')
_RE_PLUG_INDEX = re.compile(r'\[(\d+)\]$')


def _get_mnode(name):
    u"""
    ノード名から API2 の MObject を得る。
    """
    sel = _2_MSelectionList()
    sel.add(name)
    return sel.getDependNode(0)


def _mplugName(mplug, useLong=True):
    u"""
    MPlug の名前を得る。
    """
    try:
        return _2_getAPathTo(mplug.node()).partialPathName() + '.' + mplug.partialName(includeNonMandatoryIndices=True, useLongNames=useLong)
    except:
        return mplug.partialName(includeNodeName=True, includeNonMandatoryIndices=True, useLongNames=useLong)


def _printPlugChange(name, news, keeps, dels=None):
    u"""
    setCode の際の、コネクション変更の分析結果をプリント。
    """
    dic = {}
    msg = []

    for i, plug in keeps.items():
        dic[i] = plug + ' (KEEP)'
    msg.append('keep=%r' % keeps.keys())

    if dels is not None:
        for i, plug in dels.items():
            dic[i] = plug + ' (DEL)'
        msg.append('del=%r' % dels.keys())

    for i, plug in news.items():
        dic[i] = plug + ' (NEW)'
    msg.append('new=%r' % news.keys())

    for i in sorted(dic):
        print('# %s[%d] = %s' % (name, i, dic[i]))
    print('# (%s: %s)' % (name, ', '.join(msg)))


def _toRawCode(code, cur_rawcode, curInputs, curOutputs):
    u"""
    ユーザーコードを生コードに変換する。
    """
    # 現在の生コードを分析し、管理されたコネクションとそうでないものとに分類する。
    # curInputs と curOutputs 辞書から管理されたものが取り出され、残りが維持されるべきものになる。
    knownIn = {}  # plug to indices の辞書。
    knownOut = {}  # plug to index の辞書。
    for mat in _RE_IO_PLUG.finditer(cur_rawcode):
        name, idx = mat.groups()
        idx = int(idx)
        if name == 'IN':
            # 入力コネクションの無い要素は unknown 扱いとする。
            plug = curInputs.get(idx)
            if plug:
                del curInputs[idx]
                val = knownIn.get(plug)
                if val:
                    val.append(idx)
                else:
                    knownIn[plug] = [idx]
        else:
            # 出力先が複数の場合は unknown 扱いとする。
            plug = curOutputs.get(idx)
            if plug and not isinstance(plug, list):
                del curOutputs[idx]
                knownOut[plug] = idx
    #print(curInputs, knownIn)
    #print(curOutputs, knownOut)

    # 新しく入力されたコードをパースし、プラグ表記部分をリストに格納する。
    # 既存の入力プラグのインデックスが維持されるように、まずそれらを優先的に決定する。
    inputPlugToIdx = {}
    keywords = []
    for mat in _RE_PLUG.finditer(code):
        name, eq = mat.groups()
        names = cmds.ls(name)
        n = len(names)
        if n >= 2:
            raise RuntimeError('Multiple name exists: ' + name)
        if n:
            # 実際に存在するプラグ名を処理する。
            name = names[0]  # long name に統一。
            keywords.append((name, eq) + mat.span(1))
            if not eq:
                _inheritPlugIndex(inputPlugToIdx, name, knownIn, curInputs)

    # コネクションを決定する。
    # 新しく確定されたインデックス、不要になったインデックス、維持されるインデックスに分類される。
    outputPlugToIdx = {}
    inLastIdx = -1
    outLastIdx = -1
    newcode = []
    ptr = 0
    for name, eq, s, e in keywords:
        newcode.append(code[ptr:s])
        ptr = e

        # インデックスを確定する。管理されていないインデックスは維持するため避けられる。
        if eq:
            # 出力は、管理されているインデックスの維持は気にせずに再配置する。
            i, outLastIdx = _decidePlugIndex(outputPlugToIdx, name, knownOut, curOutputs, outLastIdx)
            newcode.append('OUT[%d]' % i)
        else:
            # 入力は、管理されているインデックスをなるべく変えずに再利用する。
            i, inLastIdx = _decidePlugIndex(inputPlugToIdx, name, None, curInputs, inLastIdx)
            newcode.append('IN[%d]' % i)
    newcode.append(code[ptr:])

    # 不要になったインデックス辞書は参照方向を plug to indices から index to plug に直す。
    fixedKnownIn = {}
    for plug, idxs in knownIn.items():
        for i in idxs:
            fixedKnownIn[i] = plug

    return (
        ''.join(newcode),
        dict([(i, p) for p, i in inputPlugToIdx.items() if not i in curInputs]),
        fixedKnownIn, 
        dict([(i, p) for p, i in outputPlugToIdx.items() if not i in curOutputs]),
        dict([(i, p) for p, i in knownOut.items()]),
    )


def _inheritPlugIndex(plugToIdxDict, plug, knownDict, keepDict):
    u"""
    既存プラグのインデックスを変えないように継承する。
    """
    if plugToIdxDict.get(plug) is None:
        # knownDict に管理されたプラグなら、そのインデックスが維持されるように keepDict と plugToIdxDict に格納する。
        idxs = knownDict.pop(plug, None)  # 後で切断されないようにエントリーを除去する。
        if idxs:
            for idx in idxs:
                keepDict[idx] = plug
            plugToIdxDict[plug] = idxs[0]


def _decidePlugIndex(plugToIdxDict, plug, knownDict, keepDict, lastIdx):
    u"""
    プラグのインデックスを決定する。
    """
    # plugToIdxDict 確定済みのプラグならそれを利用。
    idx = plugToIdxDict.get(plug)
    if idx is None:
        # 未確定プラグなら keepDict 内のインデックスを避けて決定。
        lastIdx += 1
        while lastIdx in keepDict:
            lastIdx += 1
        idx = lastIdx

        # 管理されたプラグインデックスと一致したら、後で切断されないようにそのエントリーを除去する。
        if knownDict and knownDict.get(plug) == idx:
            keepDict[idx] = plug
            del knownDict[plug]

        plugToIdxDict[plug] = idx
    return idx, lastIdx


def _toHumanCode(code, input, output):
    u"""
    生コードをユーザーコードに変換する。
    """
    newcode = []
    ptr = 0
    for mat in _RE_IO_PLUG.finditer(code):
        name, idx = mat.groups()
        idx = int(idx)
        if name == 'IN':
            plug = input.get(idx)
            if not plug:
                continue
        else:
            # 出力先が複数の場合は unknown 扱いとする。
            plug = output.get(idx)
            if not plug or isinstance(plug, list):
                continue
        s, e = mat.span(0)
        newcode.append(code[ptr:s])
        newcode.append(plug)
        ptr = e
    newcode.append(code[ptr:])
    return ''.join(newcode)


#def _getInputDict(node, short=False, all=False):
def _getInputDict(mfn, short=False, all=False):
    u"""
    インデクスをキーにした入力コネクション辞書を得る。
    """
    #node_i = node + '.i'
    mplug = mfn.findPlug('i', False)
    if all:
        res = dict(zip_longest([int(_RE_PLUG_INDEX.search(x).group(1)) for x in (cmds.listAttr(mplug.info, m=True) or [])], '', fillvalue=''))
    else:
        res = {}

    #conn = cmds.listConnections(node_i, s=True, d=False, c=True, p=True) or []
    #for dst, src in zip(conn[::2], cmds.ls(conn[1::2], sn=True) if short else conn[1::2]):
    #    res[int(_RE_PLUG_INDEX.search(dst).group(1))] = src

    # NOTE: (2022/4/29) ls コマンドのバグのためかショート名が得られない場合があるので、API による実装に切り替え。
    getConElem = mplug.connectionByPhysicalIndex
    mps = [getConElem(i) for i in range(mplug.numConnectedElements())]
    useLong = not short
    for i in range(mplug.numConnectedElements()):
        mp = getConElem(i)
        conn = mp.connectedTo(True, False)
        if conn:
            res[mp.logicalIndex()] = _mplugName(conn[0], useLong)

    return res


#def _getOutputDict(node, short=False):
def _getOutputDict(mfn, short=False):
    u"""
    インデクスをキーにした出力コネクション辞書を得る。
    """
    res = {}

    #conn = cmds.listConnections(node + '.o', s=False, d=True, c=True, p=True) or []
    #for src, dst in zip(conn[::2], cmds.ls(conn[1::2], sn=True) if short else conn[1::2]):
    #    idx = int(_RE_PLUG_INDEX.search(src).group(1))
    #    other = res.get(idx)
    #    if other:
    #        if isinstance(other, list):
    #            other.append(dst)
    #        else:
    #            res[idx] = [other, dst]
    #    else:
    #        res[idx] = dst

    # NOTE: (2022/4/29) ls コマンドのバグのためかショート名が得られない場合があるので、API による実装に切り替え。
    mplug = mfn.findPlug('o', False)
    getConElem = mplug.connectionByPhysicalIndex
    mps = [getConElem(i) for i in range(mplug.numConnectedElements())]
    useLong = not short
    for i in range(mplug.numConnectedElements()):
        mp = getConElem(i)
        conn = mp.connectedTo(False, True)
        if conn:
            if len(conn) == 1:
                res[mp.logicalIndex()] = _mplugName(conn[0], useLong)
            else:
                res[mp.logicalIndex()] = [_mplugName(x, useLong) for x in conn]

    return res


def _updateInputs(node, newDict, removeDict):
    u"""
    入力コネクションを更新する。
    """
    if newDict or removeDict:
        fmt = node + '.i[%d]'
        for idx in removeDict:
            if idx not in newDict:
                #print('REMOVE: ' + (fmt % idx))
                cmds.removeMultiInstance(fmt % idx, b=True)
        for idx, src in newDict.items():
            #print('CONNECT: %s -> %s' % (src, fmt % idx))
            cmds.connectAttr(src, fmt % idx, f=True)
        return True
    return False


def _updateOutputs(node, newDict, oldConnDict, idxsToKeep):
    u"""
    出力コネクションを更新する。

    既存の不要なプラグの切断や削除までが行われ、
    コネクションの新規作成は行われない。
    後で newDict を `_connectOutputs` で接続する。

    :returns: 何らかの編集が行われたかどうか。
    """
    # まず、変化がないかどうかを簡易的に判断する。
    attrs = cmds.listAttr(node + '.o', m=True) or []
    if not newDict and len(attrs) == len(idxsToKeep):
        #print('NOT_UPDATED: %s.outputs[]' % node)
        return False

    # 既存のプラグをチェックしていく。
    updated = False
    node_ = node + '.'
    for attr in attrs:
        idx = int(_RE_PLUG_INDEX.search(attr).group(1))

        # 維持すべき箇所はスキップ。
        if idx in idxsToKeep:
            #print('KEEP: ' + node_ + attr)
            continue

        # 今後必要になるコネクションか？
        plug = node_ + attr
        tgt = newDict.get(idx)
        if tgt:
            # 古いコネクションなら切断する。
            oldtgt = oldConnDict.get(idx)
            if oldtgt:
                #print('DISCONNECT: %s -> %s' % (plug, oldtgt))
                cmds.disconnectAttr(plug, oldtgt)
                updated = True

        # 不要なプラグなら削除。
        else:
            #print('REMOVE: ' + plug)
            cmds.removeMultiInstance(plug, b=True)
            updated = True
    return updated


def _connectOutputs(node, newDict):
    u"""
    出力コネクションを完了する。
    """
    fmt = node + '.o[%d]'
    for i, tgt in newDict.items():
        #print('CONNECT: %s -> %s' % (fmt % i, tgt))
        cmds.connectAttr(fmt % i, tgt, f=True)

