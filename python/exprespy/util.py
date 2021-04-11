# -*- coding: utf-8 -*-
u"""
utility module.
"""
from __future__ import absolute_import
from __future__ import print_function

import traceback
from weakref import ref as _wref

from maya.OpenMaya import (
    MSelectionList as _1_MSelectionList,
    MObject as _1_MObject,
)
from maya.api.OpenMaya import (
    MSelectionList as _2_MSelectionList,
)
import maya.cmds as cmds


#------------------------------------------------------------------------------
_finalize_refs = {}


def registerFinalizer(obj, func):
    r = _wref(obj, _finalizer)
    k = id(r)
    _finalize_refs[k] = (r, func)
    return k


def _finalizer(r):
    if _finalize_refs:
        func = _finalize_refs.pop(id(r))[1]
        try:
            func()
        except Exception:
            traceback.print_exc()


def trackDestruction(obj):
    s = repr(obj)
    def func():
        print('DESTRUCT: ' + s)
    print('BEGIN_TRACK: ' + s)
    return registerFinalizer(obj, func)


#------------------------------------------------------------------------------
def api1_mnode(name):
    u"""
    Gets a API1 MObject by name.
    """
    sel = _1_MSelectionList()
    sel.add(name)
    mobj = _1_MObject()
    sel.getDependNode(0, mobj)
    return mobj


#------------------------------------------------------------------------------
def api2_mnode(name):
    u"""
    Gets a API2 MObject by name.
    """
    sel = _2_MSelectionList()
    sel.add(name)
    return sel.getDependNode(0)


#------------------------------------------------------------------------------
class UITemplate(object):
    u"""
    mel uiTemplate wrapper class.
    """
    def __init__(self, name):
        if cmds.uiTemplate(name, ex=True):
            self._name = name
        else:
            self._name = cmds.uiTemplate(name)

    def __str__(self):
        return self._name

    def __repr__(self):
        return "%s('%s')" % (type(self).__name__, self._name)

    def __enter__(self):
        cmds.setUITemplate(self._name, pushTemplate=True)
        return self

    def __exit__(self, type, value, traceback):
        cmds.setUITemplate(popTemplate=True)

