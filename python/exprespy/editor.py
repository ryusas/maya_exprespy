# -*- coding: utf-8 -*-
u"""
Python Script Editor.
"""
from __future__ import absolute_import
from __future__ import print_function

import sys
from weakref import WeakValueDictionary as _WeakValueDictionary

import maya.cmds as cmds
import maya.mel as mel

try:
    from shiboken6 import wrapInstance
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from shiboken2 import wrapInstance
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError:
        try:
            from shiboken import wrapInstance
            from PySide import QtCore, QtGui
            import PySide.QtGui as QtWidgets
        except ImportError:
            try:
                from sip import wrapinstance as wrapInstance
                from PyQt4 import QtCore, QtGui
                import PyQt4.QtGui as QtWidgets
            except ImportError:
                wrapInstance = None

if sys.hexversion < 0x3000000:
    LONG = long
else:
    LONG = int


#------------------------------------------------------------------------------
class UIControl(object):
    u"""
    何らかの UI 要素の基底クラス。
    """
    def __init__(self, path):
        self.path = path
        self.root = path.split('|')[0]
        _INSTANCE_DICT[path] = self

        #------------------------
        #from .util import trackDestruction
        #trackDestruction(self)
        #------------------------

    def __str__(self):
        return self.path

    def __repr__(self):
        #tkns = self.path.split('|')
        #if tkns > 3:
        #    return "<%s '%s|...|%s'>" % (type(self).__name__, tkns[0], tkns[-1])
        return "<%s '%s'>" % (type(self).__name__, self.path)

    @classmethod
    def getAllInstances(cls):
        return [x for x in _INSTANCE_DICT.values() if isinstance(x, cls)]

    @staticmethod
    def getInstance(path):
        return _INSTANCE_DICT.get(path)

_INSTANCE_DICT = _WeakValueDictionary()


#------------------------------------------------------------------------------
if wrapInstance:
    from weakref import ref as _weakref
    from maya.OpenMayaUI import MQtUtil


    class ScriptEditor(UIControl):
        u"""
        Qt を使える環境用の ScriptEditor クラス。cmdScrollFieldExecuter を使用する。
        """
        def __init__(self, name='scriptEditor', path='', **kwargs):
            parentName = cmds.setParent(q=True)
            p = MQtUtil.findLayout(parentName)
            lytWd = wrapInstance(LONG(p), QtWidgets.QWidget)

            widget = ScriptEditorWidget(name, textChangeHandler=self.textChanged, **kwargs)
            lytWd.layout().addWidget(widget)
            self.__widget_ref = _weakref(widget)
            self.editor = parentName + '|' + name

            super(ScriptEditor, self).__init__(path or self.editor)

        @staticmethod
        def isRichEditor():
            return True

        def getText(self):
            return self.__widget_ref().getText()

        def setText(self, txt):
            self.__widget_ref().setText(txt)

        def textChanged(self, txt):
            pass

        def widget(self):
            return self.__widget_ref()


    class ScriptEditorWidget(QtWidgets.QWidget):
        u"""
        mel の cmdScrollFieldExecuter を scrollField と同等に使えるようにラップした Qt ウィジェット。

        scrollField の Change イベント（FocusChange）相当がとれないため、
        そのためだけ Qt の eventFilter を利用する。
        """
        def __init__(self, name='scriptEditor', parent=None, textChangeHandler=None, **kwargs):
            super(ScriptEditorWidget, self).__init__(parent)

            self.setObjectName(name)

            self.__layout = QtWidgets.QVBoxLayout(self)
            self.__layout.setContentsMargins(0,0,0,0)

            self.mayaEditor = cmds.cmdScrollFieldExecuter(
                st='python', searchWraps=True, filterKeyPress=self.__keyPress,
                cco=False, opc=False, sth=False, # acb=False,
                **kwargs)
            self.__txt = ''

            p = MQtUtil.findControl(self.mayaEditor)
            self.editor = p and wrapInstance(LONG(p), QtWidgets.QTextEdit)
            if self.editor:
                self.editor.setParent(self)
                if textChangeHandler:
                    self.__textChangeHandler = textChangeHandler
                    self.editor.installEventFilter(self)
                    #self.editor.textChanged.connect(self.__textChanged)
                self.__layout.addWidget(self.editor)

        def syncSettings(self, **kwargs):
            _syncEditorOpt(kwargs, 'sln', 'showLineNumbers', 'commandExecuterShowLineNumbers')
            #_syncEditorOpt(kwargs, 'cco', 'commandCompletion', 'commandExecuterCommandCompletion')
            #_syncEditorOpt(kwargs, 'opc', 'objectPathCompletion', 'commandExecuterPathCompletion')
            #_syncEditorOpt(kwargs, 'sth', 'showTooltipHelp', 'commandExecuterToolTipHelp')
            _syncEditorOpt(kwargs, 'tfi', 'tabsForIndent', 'commandExecuterTabsForIndent')
            #_syncEditorOpt(kwargs, 'acb', 'autoCloseBraces', 'commandExecuterAutoCloseBraces')
            _syncEditorOpt(kwargs, 'spt', 'spacesPerTab', 'commandExecuterSpacesPerTab')
            cmds.cmdScrollFieldExecuter(self.mayaEditor, e=True, **kwargs)

        def getText(self):
            return cmds.cmdScrollFieldExecuter(self.mayaEditor, q=True, t=True)

        def setText(self, txt):
            self.__txt = txt
            cmds.cmdScrollFieldExecuter(self.mayaEditor, e=True, t=txt)

        def eventFilter(self, wd, event):
            if event.type() == QtCore.QEvent.FocusOut:  # and wd == self.editor:
                txt = cmds.cmdScrollFieldExecuter(self.mayaEditor, q=True, t=True)
                if txt != self.__txt:
                    self.__txt = txt
                    cmds.undoInfo(ock=True)
                    try:
                        self.__textChangeHandler(txt)
                    finally:
                        cmds.undoInfo(cck=True)
            return super(ScriptEditorWidget, self).eventFilter(wd, event)

        def __keyPress(self, mod, key):
            if key == 'Enter' or (key == 'Return' and mod & 4):
                # スクリプト実行を無効にする。
                cmds.cmdScrollFieldExecuter(self.mayaEditor, e=True, it='\n')
                return 1
            if key == '\x06':
                # 標準サーチウィンドウが利用可能ならそれを開く。
                if _getCurrentExecuterControl:
                    global _SEARCH_WINDOW_OWNER
                    _SEARCH_WINDOW_OWNER = self.mayaEditor
                    if cmds.window(_SEARCH_WINDOW_NAME, ex=True):
                        mel.eval('createSearchAndReplaceWindow')
                    else:
                        mel.eval('createSearchAndReplaceWindow')
                        if cmds.window(_SEARCH_WINDOW_NAME, ex=True):
                            cmds.scriptJob(uid=(_SEARCH_WINDOW_NAME, _customSearchDone))
                        else:
                            _SEARCH_WINDOW_OWNER = None
                return 1

    # 標準サーチウィンドウを利用する為に mel プロシジャ getCurrentExecuterControl をオーバーライドする。
    if mel.eval('exists getCurrentExecuterControl') and mel.eval('exists createSearchAndReplaceWindow'):
        def _getCurrentExecuterControl():
            global _SEARCH_WINDOW_OWNER
            if _SEARCH_WINDOW_OWNER:
                if cmds.cmdScrollFieldExecuter(_SEARCH_WINDOW_OWNER, ex=True):
                    return _SEARCH_WINDOW_OWNER
                _SEARCH_WINDOW_OWNER = None
            try:
                layout = mel.eval('$gCommandExecuterTabs=$gCommandExecuterTabs')
            except:
                return ''
            tabs = cmds.tabLayout(layout, q=True, ca=True)
            i = cmds.tabLayout(layout, q=True, selectTabIndex=True) - 1
            return cmds.layout(tabs[i], q=True, ca=True)[0]

        def _customSearchDone(*args):
            global _SEARCH_WINDOW_OWNER
            _SEARCH_WINDOW_OWNER = None

        _SEARCH_WINDOW_OWNER = None
        _SEARCH_WINDOW_NAME = 'commandSearchAndReplaceWnd'

        mel.eval('global proc string getCurrentExecuterControl(){ return python("%s._getCurrentExecuterControl()"); }' % __name__)
        print('# mel proc getCurrentExecuterControl is overriden by exprespy.')
    else:
        _getCurrentExecuterControl = None


    def _syncEditorOpt(dic, ln, sn, ovn):
        if not(ln in dic or sn in dic):
            dic[sn] = cmds.optionVar(q=ovn)


else:
    class ScriptEditor(UIControl):
        u"""
        Qt を使えない環境用の ScriptEditor クラス。scrollField を使用する。
        """
        def __init__(self, name='scriptEditor', path='', **kwargs):
            self.__txt = ''
            self.editor = cmds.scrollField(name, cc=self.__focusOut, **kwargs)
            super(ScriptEditor, self).__init__(path or self.editor)

        @staticmethod
        def isRichEditor():
            return False

        def getText(self):
            return cmds.scrollField(self.editor, q=True, tx=True)

        def setText(self, txt):
            self.__txt = txt
            cmds.scrollField(self.editor, e=True, tx=txt)

        def textChanged(self, txt):
            pass

        def __focusOut(self, *args):
            txt = cmds.scrollField(self.editor, q=True, tx=True)
            if txt != self.__txt:
                self.__txt = txt
                self.textChanged(txt)

