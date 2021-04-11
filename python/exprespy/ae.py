# -*- coding: utf-8 -*-
u"""
exprespy's AETemplate module.
"""
from __future__ import absolute_import

from functools import partial as _partial
#import traceback
import maya.cmds as cmds
import maya.mel as mel

from maya.OpenMaya import (
    MNodeMessage as _1_MNodeMessage,
)
_1_ConnChangeBits = _1_MNodeMessage.kConnectionMade | _1_MNodeMessage.kConnectionBroken
_1_ArrayAttrBigts = _1_MNodeMessage.kAttributeArrayAdded | _1_MNodeMessage.kAttributeArrayRemoved
_1_ConnAndArrayChangeBits = _1_ConnChangeBits | _1_ArrayAttrBigts

from .cmd import setCode, getCode
from .editor import ScriptEditor, UIControl
from .util import api1_mnode, api2_mnode, UITemplate


#------------------------------------------------------------------------------
def code_new(plug):
    #print('code_new: ' + plug)
    ExprespyEditor('codeEd').setNode(plug.split('.')[0], True)


def code_replace(plug):
    #print('code_replace: ' + plug)
    ExprespyEditor.getInstance(cmds.setParent(q=True) + '|codeEd').setNode(plug.split('.')[0])


def input_new(plug):
    #print('input_new: ' + plug)
    InputButtons('input').setNode(plug.split('.')[0], True)


def input_replace(plug):
    #print('input_replace: ' + plug)
    InputButtons.getInstance(cmds.setParent(q=True) + '|input').setNode(plug.split('.')[0])


#------------------------------------------------------------------------------
class UINodeTracker(UIControl):
    u"""
    UI オブジェクトに紐付けるノードトラッカー。

    exprespy ノードの .input[] の増減やコネクション変更を監視する。
    """
    def __init__(self, path):
        super(UINodeTracker, self).__init__(path)
        self._mnode = None
        self._cid_attrChanged = None
        cmds.scriptJob(uid=(self.path, self._killApiattrChanged))  # これによって UI が削除されるまで生きる。
        self._callbacks = []

    def setNode(self, node):
        mnode = api2_mnode(node)
        if not self._mnode or self._mnode != mnode:
            if self._cid_attrChanged:
                #print('KILL APICB', self.root)
                _1_MNodeMessage.removeCallback(self._cid_attrChanged)
            self._mnode = mnode
            #print('NEW APICB', self.root)
            self._cid_attrChanged = _1_MNodeMessage.addAttributeChangedCallback(api1_mnode(node), self._apiAttrChanged)
            self._jid_nodeDeleted = cmds.scriptJob(p=self.path, rp=True, nd=(node, self._killApiattrChanged))

            self._inputChangeProcNode = node
            self._inputChangedProc()
            return True
        return False

    def registerCallback(self, func):
        self._callbacks.append(func)

    def _killApiattrChanged(self):
        u"""
        ノード削除時、UI 削除時に API コールバックを kill する。
        """
        if self._cid_attrChanged:
            #print('KILL APICB', self.root)
            _1_MNodeMessage.removeCallback(self._cid_attrChanged)
            self._cid_attrChanged = None
            self._jid_nodeDeleted = None  # nodeDeleted ジョブは自動削除されるので ID をクリアしておく。
            self._mnode = None

    def _apiAttrChanged(self, msg, mplug, other_mp, clientdata):
        #print('AttrChanged', msg, mplug.info(), msg & _1_ConnAndArrayChangeBits, not self._inputChangeProcNode)
        if (msg & _1_ConnAndArrayChangeBits) and not self._inputChangeProcNode:
            # コネクション変更かマルチアトリビュートの増減があった時。
            tkns = mplug.info().split('.')
            if tkns[1].split('[')[0] == 'input':
                self._inputChangeProcNode = tkns[0]
                cmds.evalDeferred(self._inputChangedProc)

            # Copy Tab したアトリビュートエディタは、フレームの閉じるボタンで閉じれば消滅するが、
            # ウィンドウ内の Close ボタンで閉じると vis=False 状態で残ってしまう。(maya 2017 win64 調べ)
            # New Scene したら削除されるようだが、それまでの間も不要な API コールバックが残り続けるのを避けるため、
            # ジョブが呼ばれた際に vis をチェックして kill する。
            # オブジェクト自体はウィンドウが削除されるまで残ってしまうが、まあ良いとする。
            if not _isUIVisible(self.root):
                #print('KILL APICB & node reference', self.root)
                if self._cid_attrChanged:
                    _1_MNodeMessage.removeCallback(self._cid_attrChanged)
                    self._cid_attrChanged = None
                self._mnode = None

                if self._jid_nodeDeleted:
                    try:
                        cmds.scriptJob(k=self._jid_nodeDeleted, f=True)
                        #print('KILL nodeDeleted JOB', self.root)
                    except:
                        pass
                    self._jid_nodeDeleted = None

    def _inputChangedProc(self):
        #print('_inputChangedProc', self._inputChangeProcNode)
        if self._inputChangeProcNode:
            for func in self._callbacks:
                try:
                    func(self._inputChangeProcNode)
                #except Exception:
                #    traceback.print_exc()
                except:
                    pass
            self._inputChangeProcNode = None


def _decideTrackerUIPath(child):
    tkns = child.split('|')
    tkns.pop()
    while tkns:
        path = '|'.join(tkns)
        tkns.pop()
        if cmds.frameLayout(path, ex=True):
            if not tkns:
                break
            return '|'.join(tkns)


#------------------------------------------------------------------------------
class InputButtons(UIControl):
    u"""
    input アトリビュートの状態を反映し、削除したり出来るボタン群。
    """
    def __init__(self, name):
        super(InputButtons, self).__init__(cmds.columnLayout('input')) #, adj=True)
        self._trackerPath = _decideTrackerUIPath(self.path)
        # これによって UINodeTracker が UI と共に死ぬまで生きる。
        (UINodeTracker.getInstance(self._trackerPath) or UINodeTracker(self._trackerPath)).registerCallback(self._refresh)

    def setNode(self, node, forceUpdate=False):
        if not UINodeTracker.getInstance(self._trackerPath).setNode(node) and forceUpdate:
            self._refresh(node)

    def _refresh(self, node):
        #print('InputButtons._refresh: ' + node)
        try:
            lastParentLayout = cmds.setParent(q=True)
            cmds.setParent(self.path)

            with UITemplate('DefaultTemplate'):
                node_i = node + '.i'
                attrs = cmds.listAttr(node_i, m=True) or []

                conn = cmds.listConnections(node_i, s=True, d=False, c=True, p=True) or []
                conn = dict(zip(conn[::2], conn[1::2]))

                lyt_ = self.path + '|'
                children = [(lyt_ + x) for x in (cmds.layout(self.path, q=True, ca=True) or [])]
                nChildren = len(children)

                i = 0
                node_ = node + '.'
                for attr in attrs:
                    if i < nChildren:
                        row = children[i]
                        cmds.text(row + '|name', e=True, l=attr)
                        upstream = row + '|upstream'
                        trash = row + '|trash'
                    else:
                        row = cmds.rowLayout(nc=3, h=20, cw=[(2, 30), (3, 30)])
                        cmds.text('name', l=attr)
                        upstream = cmds.symbolButton('upstream', i='hsUpStreamCon.png', h=20)
                        trash = cmds.symbolButton('trash', i='smallTrash.png', h=20)
                        cmds.setParent('..')

                    plug = node_ + attr
                    src = conn.get(plug)
                    if src:
                        cmds.symbolButton(upstream, e=True, en=True, c=_partial(_showUpstream, plug))
                    else:
                        cmds.symbolButton(upstream, e=True, en=False)
                    cmds.symbolButton(trash, e=True, c=_callback(cmds.evalEcho, 'removeMultiInstance -b 1 ' + plug))

                    i += 1

                for i in range(i, nChildren):
                    cmds.deleteUI(children[i])

        finally:
            if lastParentLayout:
                cmds.setParent(lastParentLayout)


def _showUpstream(plug, *args):
    src = cmds.listConnections(plug, s=True, d=False)
    if src:
        mel.eval('showEditorExact ' + src[0])


#------------------------------------------------------------------------------
class ExprespyEditor(ScriptEditor):
    u"""
    スクリプトエディタと各種チェックボックス群。
    """
    _OPT_DEFAULTS = {
        'lineNumber': True,
        'rawMode': False,
        'shortName': False,
        'height': 380,
    }

    def __init__(self, name):
        with UITemplate('Exprespy'):
            def _separatorMoved():
                h = cmds.layout(form1, q=True, h=True) + h2
                ExprespyEditor.setOpt('height', h)
                #print(h)
                cmds.paneLayout(pane, e=True, h=h, ps=(1, 100, 99))

            pane = cmds.paneLayout(name, cn='horizontal2', ps=(1, 100, 99), st=5, smc=_separatorMoved, h=self.getOpt('height'))

            form1 = cmds.formLayout('form1')

            super(ExprespyEditor, self).__init__(path=pane)

            cmds.formLayout(
                form1, e=True,
                af=[
                    (self.editor, 'top', 0),
                    (self.editor, 'left', 0),
                    (self.editor, 'right', 0),
                    (self.editor, 'bottom', 0),
                ],)

            cmds.setParent(pane)

            form2 = cmds.formLayout('form2')
            rawl = cmds.rowLayout('rawl', nc=3)
            if self.isRichEditor():
                sln = self.getBoolOpt('lineNumber')
                self.widget().syncSettings(sln=sln)
                cmds.checkBox('lineNumber', l='Line Number', v=sln, cc=ExprespyEditor._lineNumber_changed)
            else:
                cmds.text(l=' ')
            cmds.checkBox('rawMode', l='Raw Mode', v=self.getBoolOpt('rawMode'), cc=ExprespyEditor._rawMode_changed)
            cmds.checkBox('shortName', l='Short Name', v=self.getBoolOpt('shortName'), cc=ExprespyEditor._shortName_changed)
            h2 = cmds.layout(rawl, q=True, h=True)
            cmds.setParent('..')
            self._inputsAPI1 = cmds.checkBox('inputsAPI1', l='Inputs API 1.0 MObject')
            cmds.formLayout(
                form2, e=True,
                af=[
                    (rawl, 'top', 0),
                    (rawl, 'left', 0),
                    (self._inputsAPI1, 'top', 0),
                    (self._inputsAPI1, 'right', 0),
                ],)

        # これによって UINodeTracker が UI と共に死ぬまで生きる。
        self._trackerPath = _decideTrackerUIPath(self.path)
        (UINodeTracker.getInstance(self._trackerPath) or UINodeTracker(self._trackerPath)).registerCallback(self._refresh)

    def setNode(self, node, forceUpdate=False):
        #print('setNode: ' + node)
        self._ignoreCodeChange = False
        self._node = node
        cmds.connectControl(self._inputsAPI1, node + '.inputsAsApi1Object')

        self._jid_codeAttrChange = cmds.scriptJob(p=self.path, rp=True, ac=(node + '.cd', self._codeAttrChanged))
        #print('NEW JOB (cd)', self._jid_codeAttrChange)
        cmds.scriptJob(p=self._inputsAPI1, rp=True, nd=(node, self._nodeDeleted))

        if not UINodeTracker.getInstance(self._trackerPath).setNode(node) and forceUpdate:
            self._refresh(node)

    def textChanged(self, txt):
        #print('EditorChanged: ' + self._node)
        rawMode = self.getBoolOpt('rawMode')
        if rawMode:
            self._ignoreCodeChange = True
        setCode(self._node, txt, raw=rawMode)

    def _refresh(self, node):
        #print('ExprespyEditor._refresh: ' + node)
        try:
            txt = getCode(node, raw=self.getBoolOpt('rawMode'), short=self.getBoolOpt('shortName'))
        except:
            txt = ''
        self.setText(txt)

    def _codeAttrChanged(self):
        #print('AttrChanged: %s %r' % (self._node, self._ignoreCodeChange))
        if self._ignoreCodeChange:
            self._ignoreCodeChange = False
            return
        self._refresh(self._node)

        # Copy Tab したアトリビュートエディタは、フレームの閉じるボタンで閉じれば消滅するが、
        # ウィンドウ内の Close ボタンで閉じると vis=False 状態で残ってしまう。(maya 2017 win64 調べ)
        # New Scene したら削除されるようだが、それまでの間も不要な scriptJob が残り続けるのを避けるため、
        # ジョブが呼ばれた際に vis をチェックして kill する。
        # オブジェクト自体はウィンドウが削除されるまで残ってしまうが、まあ良いとする。
        jid = self._jid_codeAttrChange
        if jid and not _isUIVisible(self.root):
            self._jid_codeAttrChange = None
            #print('KILL %d, %s' % (jid, self.root))
            cmds.evalDeferred(lambda: cmds.scriptJob(k=jid, f=True))

    def _nodeDeleted(self):
        #print('NodeDeleted: ' + self.path)
        if self._jid_codeAttrChange:
            #print('KILL %d, %s' % (self._jid_codeAttrChange, self.root))
            cmds.scriptJob(k=self._jid_codeAttrChange, f=True)
            self._jid_codeAttrChange = None

    @staticmethod
    def _lineNumber_changed(val):
        ExprespyEditor.setOpt('lineNumber', val)
        for ctl in ExprespyEditor.getAllInstances():
            if ctl.isRichEditor():
                ctl.widget().syncSettings(sln=val)

    @staticmethod
    def _rawMode_changed(val):
        ExprespyEditor.setOpt('rawMode', val)
        for ctl in ExprespyEditor.getAllInstances():
            ctl._codeAttrChanged()

    @staticmethod
    def _shortName_changed(val):
        ExprespyEditor.setOpt('shortName', val)
        for ctl in ExprespyEditor.getAllInstances():
            ctl._codeAttrChanged()

    @staticmethod
    def getBoolOpt(key):
        name = 'exprespy.' + key
        if cmds.optionVar(ex=name):
            return bool(cmds.optionVar(q=name))
        return ExprespyEditor._OPT_DEFAULTS[key]

    @staticmethod
    def getOpt(key):
        name = 'exprespy.' + key
        if cmds.optionVar(ex=name):
            return cmds.optionVar(q=name)
        return ExprespyEditor._OPT_DEFAULTS[key]

    @staticmethod
    def setOpt(key, val):
        name = 'exprespy.' + key
        if ExprespyEditor._OPT_DEFAULTS[key] == val:
            if cmds.optionVar(ex=name):
                cmds.optionVar(rm=name)
        else:
            cmds.optionVar(iv=(name, int(val)))


#------------------------------------------------------------------------------
_callback = lambda f, *a: lambda b: f(*a)


def _isUIVisible(wnd):
    u"""
    コントロールが可視状態かどうか。
    """
    try:
        return cmds.control(wnd, q=True, vis=True)
    except:
        return True  # 予期せぬ事態の場合は余計なことをしないようにする。

