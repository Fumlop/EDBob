from __future__ import annotations

from src.core import EDAP_data
# from src.screen.OCR import OCR
from src.ed.StatusParser import StatusParser
from src.ed import MenuNav


class EDShipControl:
    """ Handles ship control, FSD, SC, etc. """
    def __init__(self, ed_ap, screen, keys, cb):
        self.ocr = ed_ap.ocr
        self.screen = screen
        self.keys = keys
        self.status_parser = StatusParser()
        self.ap_ckb = cb

    def goto_cockpit_view(self) -> bool:
        """ Goto cockpit view.
        @return: True once complete.
        """
        return MenuNav.goto_cockpit(self.keys, self.status_parser)
