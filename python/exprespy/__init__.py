# -*- coding: utf-8 -*-
u"""
Support module for exprespy plug-in.

How to refresh AE:
python("import sys; [sys.modules.pop(k) for k in list(sys.modules) if k.startswith('exprespy')]");
source AEexprespyTemplate;
refreshEditorTemplates;
"""
__version__ = '2.0.2.20180828'

from .cmd import *

