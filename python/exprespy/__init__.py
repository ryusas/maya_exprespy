# -*- coding: utf-8 -*-
u"""
Support module for exprespy plug-in.

How to refresh AE:
python("import sys; [sys.modules.pop(k) for k in list(sys.modules) if k.startswith('exprespy')]");
source AEexprespyTemplate;
refreshEditorTemplates;
"""
from __future__ import absolute_import

__version__ = '3.0.1.20220627'

from .cmd import *

