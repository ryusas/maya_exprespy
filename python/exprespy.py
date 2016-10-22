# -*- coding: utf-8 -*-
u"""
Support module for exprespy plug-in.
"""
__version__ = '1.0.1.20161022'

from functools import partial as _partial
import re
import maya.cmds as cmds

_RE_PLUG = re.compile(r'([\|\:]?[a-zA-Z_]\w*(?:[\|\:][a-zA-Z_]\w*)*(?:\.[a-zA-Z_]\w*(?:\[\d+\])?)+)(\s*\=)?')
_RE_IO_PLUG = re.compile(r'(IN|OUT)\[(\d+)\]')
_RE_PLUG_INDEX = re.compile(r'\[(\d+)\]$')


#------------------------------------------------------------------------------
def create(code=''):
    u"""
    exprespy ノードを新規生成し、コード文字列をセットする。
    """
    cmds.loadPlugin('exprespy', qt=True)
    node = cmds.createNode('exprespy')
    setCode(node, code)
    return node


def setCode(node, code):
    u"""
    exprespy ノードにコード文字列をセットする。
    """
    unknownIn = _getInputDict(node)
    unknownOut = _getOutputDict(node)
    rawcode = cmds.getAttr(node + '.cd') or ''
    knownIn, knownOut = _analyzeRawCode(rawcode, unknownIn, unknownOut)

    newcode, newIn, newOut = _toRawCode(code, unknownIn, unknownOut)

    #print('unknownIn=' + repr(unknownIn.keys()))
    #print('unknownOut=' + repr(unknownOut.keys()))
    #print('knownIn=' + repr(knownIn.keys()))
    #print('knownOut=' + repr(knownOut.keys()))
    #print('newIn=' + repr(newIn.keys()))
    #print('newOut=' + repr(newOut.keys()))

    outUpdated = _updateOutputs(node, newOut, knownOut, unknownOut)
    if newcode == rawcode:
        if not(_updateInputs(node, newIn, knownIn, unknownIn) or outUpdated or newOut):
            cmds.setAttr(node + '.cd', newcode, type='string')
    else:
        cmds.setAttr(node + '.cd', '', type='string')
        _updateInputs(node, newIn, knownIn, unknownIn)
        cmds.setAttr(node + '.cd', newcode, type='string')
    if newOut:
        _connectOutputs(node, newOut)


def getCode(node):
    u"""
    exprespy ノードからコード文字列を得る。
    """
    return _toHumanCode(
        cmds.getAttr(node + '.cd') or '',
        _getInputDict(node),
        _getOutputDict(node),
    )


#------------------------------------------------------------------------------
def ae_code_new(node):
    #print('ae_code_new: ' + node)
    if not cmds.uiTemplate('Exprespy', ex=True):
        cmds.uiTemplate('Exprespy')
    cmds.setUITemplate('Exprespy', pushTemplate=True)
    ctl = cmds.scrollField('codeEd', h=500)
    cmds.setUITemplate(popTemplate=True)
    cmds.scrollField(ctl, e=True, tx=getCode(node), cc=_partial(_ae_setCode, ctl, node))
    cmds.scriptJob(p=ctl, rp=True, ac=(node + '.cd', _partial(_ae_codeChange, ctl, node)))


def ae_code_replace(node):
    #print('ae_code_replace: ' + node)
    ctl = cmds.setParent(q=True) + '|codeEd'
    cmds.scrollField(ctl, e=True, tx=getCode(node), cc=_partial(_ae_setCode, ctl, node))
    cmds.scriptJob(p=ctl, rp=True, ac=(node + '.cd', _partial(_ae_codeChange, ctl, node)))


def _ae_setCode(ctl, node, *args):
    #print('_ae_setCode: ' + node)
    global _IGNORE_CODE_CHANGE
    _IGNORE_CODE_CHANGE = True
    setCode(node, cmds.scrollField(ctl, q=True, tx=True))

_IGNORE_CODE_CHANGE = False


def _ae_codeChange(ctl, node, *args):
    global _IGNORE_CODE_CHANGE
    if _IGNORE_CODE_CHANGE:
        _IGNORE_CODE_CHANGE = False
        return
    #print('_ae_codeChange: ' + node)
    cmds.scrollField(ctl, e=True, tx=getCode(node))


#------------------------------------------------------------------------------
def _decideConnIndex(revDict, plug, unknownSet, lastIdx):
    idx = revDict.get(plug)
    if idx is None:
        idx = lastIdx + 1
        while idx in unknownSet:
            idx += 1
        revDict[plug] = idx
    return idx


def _toRawCode(code, unknownInSet, unknownOutSet, short=False):
    u"""
    ユーザーコードを生コードに変換する。
    """
    inputIdxDict = {}
    outputIdxDict = {}
    inIdx = -1
    outIdx = -1
    newcode = []
    ptr = 0
    for mat in _RE_PLUG.finditer(code):
        name, eq = mat.groups()
        if cmds.objExists(name):
            names = cmds.ls(name, sn=short)
            if len(names) >= 2:
                raise RuntimeError('Multiple name exists: ' + name)
            name = names[0]
            s, e = mat.span(1)
            newcode.append(code[ptr:s])
            if eq:
                i = _decideConnIndex(outputIdxDict, name, unknownOutSet, outIdx)
                newcode.append('OUT[%d]' % i)
                outIdx = max(i, outIdx)
            else:
                i = _decideConnIndex(inputIdxDict, name, unknownInSet, inIdx)
                newcode.append('IN[%d]' % i)
                inIdx = max(i, inIdx)
            ptr = e
    newcode.append(code[ptr:])
    return (
        ''.join(newcode),
        dict([(i, v) for v, i in inputIdxDict.items()]),
        dict([(i, v) for v, i in outputIdxDict.items()]),
    )


def _analyzeRawCode(code, input, output):
    u"""
    生コードを分析し、管理されたコネクションとそうでないものとに分類する。

    input と output 辞書から管理されたものが取り出され、
    残りが管理されていないものになる。
    """
    knownIn = {}
    knownOut = {}
    for mat in _RE_IO_PLUG.finditer(code):
        name, idx = mat.groups()
        idx = int(idx)
        if name == 'IN':
            plug = input.pop(idx, None)
            if plug:
                knownIn[idx] = plug
        else:
            # 出力先が複数の場合は unknown 扱いとする。
            plug = output.get(idx)
            if plug and not isinstance(plug, list):
                del output[idx]
                knownOut[idx] = plug
    return knownIn, knownOut


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


def _getInputDict(node):
    u"""
    インデクスをキーにした入力コネクション辞書を得る。
    """
    res = {}
    conn = cmds.listConnections(node + '.i', s=True, d=False, c=True, p=True) or []
    for src, dst in zip(conn[1::2], conn[::2]):
        res[int(_RE_PLUG_INDEX.search(dst).group(1))] = src
    return res


def _getOutputDict(node):
    u"""
    インデクスをキーにした出力コネクション辞書を得る。
    """
    res = {}
    conn = cmds.listConnections(node + '.o', s=False, d=True, c=True, p=True) or []
    for src, dst in zip(conn[::2], conn[1::2]):
        idx = int(_RE_PLUG_INDEX.search(src).group(1))
        other = res.get(idx)
        if other:
            if isinstance(other, list):
                other.append(dst)
            else:
                res[idx] = [other, dst]
        else:
            res[idx] = dst
    return res


def _updateInputs(node, newDict, knownDict, unknownDict):
    u"""
    入力コネクションを更新する。

    newDict はチェック処理に使われるため、その内容は維持されない。
    """
    # まず、変化がないかどうかを簡易的に判断する。
    attrs = cmds.listAttr(node + '.i', m=True) or []
    n = len(attrs) - len(unknownDict)
    if n == len(knownDict) and n == len(newDict) and knownDict == newDict:
        #print('NOT_UPDATED: %s.inputs[]' % node)
        return False

    # 既存のプラグをチェックしていく。
    updated = False
    node_ = node + '.'
    for attr in attrs:
        idx = int(_RE_PLUG_INDEX.search(attr).group(1))

        # 知らないコネクションなら維持する。
        if idx in unknownDict:
            #print('KEEP: ' + node_ + attr)
            continue

        # 今後必要になるコネクションか？
        plug = node_ + attr
        tgt = newDict.pop(idx, None)
        if tgt:
            # 既に同じコネクションが在ればそのまま維持。
            if tgt == knownDict.get(idx):
                #print('NOT_CHANGED: ' + plug)
                continue

            # 古いコネクションが在れば、そのまま新規に接続し直す。
            #print('CONNECT: %s -> %s' % (tgt, plug))
            cmds.connectAttr(tgt, plug, f=True)
            updated = True

        # 不要なプラグなら削除。
        else:
            #print('REMOVE: ' + plug)
            cmds.removeMultiInstance(plug, b=True)
            updated = True

    # 未処理のプラグを全てコネクトする。
    if newDict:
        fmt = node + '.i[%d]'
        for i, tgt in newDict.items():
            #print('NEW_CONNECT: %s -> %s' % (tgt, fmt % i))
            cmds.connectAttr(tgt, fmt % i, f=True)
        return True
    return updated 


def _updateOutputs(node, newDict, knownDict, unknownDict):
    u"""
    出力コネクションを更新する。

    既存の不要なプラグの切断や削除までが行われ、
    コネクションの新規作成は行われない。
    後で newDict に残されたものを `_connectOutputs` で接続する。

    :returns: 何らかの編集が行われたかどうか。
    """
    # まず、変化がないかどうかを簡易的に判断する。
    attrs = cmds.listAttr(node + '.o', m=True) or []
    n = len(attrs) - len(unknownDict)
    if n == len(knownDict) and n == len(newDict) and knownDict == newDict:
        #print('NOT_UPDATED: %s.outputs[]' % node)
        newDict.clear()
        return False

    # 既存のプラグをチェックしていく。
    updated = False
    node_ = node + '.'
    for attr in attrs:
        idx = int(_RE_PLUG_INDEX.search(attr).group(1))

        # 知らないコネクションなら維持する。
        if idx in unknownDict:
            #print('KEEP: ' + node_ + attr)
            continue

        # 今後必要になるコネクションか？
        plug = node_ + attr
        tgt = newDict.get(idx)
        if tgt:
            # 既に同じコネクションが在ればそのまま維持。
            oldtgt = knownDict.get(idx)
            if tgt == oldtgt:
                #print('NOT_CHANGED: ' + plug)
                del newDict[idx]
                continue
            # 古いコネクションなら切断する。
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
        #print('NEW_CONNECT: %s -> %s' % (fmt % i, tgt))
        cmds.connectAttr(fmt % i, tgt, f=True)

