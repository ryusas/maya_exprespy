# -*- coding: utf-8 -*-
u"""
Support module for exprespy plug-in.
"""

from functools import partial as _partial
import re
import maya.cmds as cmds

_RE_PLUG = re.compile(r'(\w+(?:\.\w+(?:\[\d+\])?)+)(\s*\=)?')
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
    newcode, input, output = _toRawCode(code)

    outUpdated = _updateOutputConnections(node, output, noConn=True)
    if newcode == cmds.getAttr(node + '.cd'):
        if not(_updateInputConnections(node, input) or outUpdated):
            cmds.setAttr(node + '.cd', newcode, type='string')
    else:
        cmds.setAttr(node + '.cd', '', type='string')
        _updateInputConnections(node, input)
        cmds.setAttr(node + '.cd', newcode, type='string')
    if outUpdated:
        _connectOutputs(node, output)


def getCode(node):
    u"""
    exprespy ノードからコード文字列を得る。
    """
    input = _getInputDict(node)
    output = _getOutputDict(node)
    code = cmds.getAttr(node + '.cd') or ''
    return _toHumanCode(code, input, output)


#------------------------------------------------------------------------------
def ae_code_new(node):
    #print('ae_code_new: ' + node)
    cmds.uiTemplate()
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
def _appendToList(lst, item):
    try:
        idx = lst.index(item)
    except ValueError:
        idx = len(lst)
        lst.append(item)
    return idx


def _toRawCode(code, short=False):
    u"""
    ユーザーコードをアトリビュート用コードに変換する。
    """
    input = []
    output = []
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
                newcode.append('OUT[%d]' % _appendToList(output, name))
            else:
                newcode.append('IN[%d]' % _appendToList(input, name))
            ptr = e
    newcode.append(code[ptr:])
    input = dict([(i, v) for i, v in enumerate(input)])
    output = dict([(i, v) for i, v in enumerate(output)])
    return ''.join(newcode), input, output


def _toHumanCode(code, input, output):
    u"""
    アトリビュート用コードをユーザーコードに変換する。
    """
    newcode = []
    ptr = 0
    for mat in _RE_IO_PLUG.finditer(code):
        name, idx = mat.groups()
        idx = int(idx)
        if name == 'IN':
            plug = input.get(idx)
        else:
            plug = output.get(idx)
        if plug:
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
        res[int(_RE_PLUG_INDEX.search(src).group(1))] = dst
    return res


def _updateInputConnections(node, input):
    u"""
    入力コネクションを更新する。
    """
    attrs = cmds.listAttr(node + '.i', m=True) or []
    if len(attrs) == len(input) and _getInputDict(node) == input:
        return False

    node_ = node + '.'
    for attr in attrs:
        cmds.removeMultiInstance(node_ + attr, b=True)

    fmt = node + '.i[%d]'
    for i, src in input.items():
        cmds.connectAttr(src, fmt % i, f=True)

    return True


def _updateOutputConnections(node, output, noConn=False):
    u"""
    出力コネクションを更新する。
    """
    curoutput = _getOutputDict(node)
    attrs = cmds.listAttr(node + '.o', m=True) or []
    if len(attrs) == len(output) and curoutput == output:
        return False

    node_ = node + '.'
    for attr in attrs:
        cmds.removeMultiInstance(node_ + attr, b=True)
        #dst = curoutput.get(int(_RE_PLUG_INDEX.search(attr).group(1)))
        #src = node_ + attr
        #if dst:
        #    print(src, dst, cmds.getAttr(dst))
        #    cmds.disconnectAttr(src, dst)
        #cmds.removeMultiInstance(src)

    if not noConn:
        _connectOutputs(node, output)

    return True


def _connectOutputs(node, output):
    u"""
    先に全て削除済みの出力コネクションを再生成する。
    """
    fmt = node + '.o[%d]'
    for i, dst in output.items():
        cmds.connectAttr(fmt % i, dst, f=True)

