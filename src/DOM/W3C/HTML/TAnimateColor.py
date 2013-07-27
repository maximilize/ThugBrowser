#!/usr/bin/env python

import string
import logging
from .HTMLElement import HTMLElement

log = logging.getLogger("Thug")


class TAnimateColor(HTMLElement):
    def __init__(self, doc, tag):
        self.doc = doc
        self.tag = tag
        self._values = ""

    def get_values(self):
        return self._values

    def set_values(self, values):
        log.DFT.check_shellcode(values)
        self._values = values

    values = property(get_values, set_values)
