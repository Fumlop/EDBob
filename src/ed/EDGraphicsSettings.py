from os.path import isfile

import xmltodict
from os import environ

from src.core.EDlogger import logger


class EDGraphicsSettings:
    """ Reads Elite Dangerous graphics XML files to extract FOV and screen settings. """

    def __init__(self, display_file_path=None, settings_file_path=None):
        base = environ['LOCALAPPDATA'] + "\\Frontier Developments\\Elite Dangerous\\Options\\Graphics\\"
        self.display_settings_filepath = display_file_path or (base + "DisplaySettings.xml")
        self.settings_filepath = settings_file_path or (base + "Settings.xml")

        for path in (self.display_settings_filepath, self.settings_filepath):
            if not isfile(path):
                raise FileNotFoundError(f"ED graphics file not found: {path}")

        display = self._read_xml(self.display_settings_filepath)['DisplayConfig']
        self.screenwidth = display['ScreenWidth']
        self.screenheight = display['ScreenHeight']

        settings = self._read_xml(self.settings_filepath)
        self.fov = settings['GraphicsOptions']['FOV']

        logger.info(f"ED Graphics: {self.screenwidth}x{self.screenheight} FOV={self.fov}")

    @staticmethod
    def _read_xml(filename) -> dict:
        with open(filename, 'r') as f:
            return xmltodict.parse(f.read())
