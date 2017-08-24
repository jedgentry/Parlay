import logging
import sys
from twisted.python import log
from twisted.python.log import textFromEventDict, _safeFormat
from twisted.python.util import untilConcludes


class LevelFileLogObserver(log.FileLogObserver):

    def __init__(self, level=logging.INFO):
        log.FileLogObserver.__init__(self, sys.stdout)
        self.logLevel = level

    def emit(self, event_dict):
        if event_dict['isError']:
            level = logging.ERROR
        elif 'level' in event_dict:
            level = event_dict['level']
        else:
            level = logging.INFO
        if level == self.logLevel:
            self.log_dictionary(event_dict, level)

    def log_dictionary(self, event_dict, level):
        """
        Format the given log event as text and write it to the output file.

        @param event_dict: a log event
        @type event_dict: L{dict} mapping L{str} (native string) to L{object}
        
        @param level: The event level to log.
        """
        text = textFromEventDict(event_dict)
        if text is None:
            return

        time_str = self.formatTime(event_dict["time"])
        fmt_dict = {
            "system": event_dict["system"],
            "text": text.replace("\n", "\n\t")
        }
        msg_str = _safeFormat("[%(system)s] %(text)s\n", fmt_dict)
        untilConcludes(logging.getLogger('parlay').log, level, time_str + " " + msg_str)
