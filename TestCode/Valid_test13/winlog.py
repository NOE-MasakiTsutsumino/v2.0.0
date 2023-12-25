from win32evtlog import OpenEventLog, ReportEvent, EVENTLOG_INFORMATION_TYPE, EVENTLOG_WARNING_TYPE, EVENTLOG_ERROR_TYPE

class WindowsEventLogger:

    def __init__(self, logger_name: str):
        self.handle = OpenEventLog(None, logger_name)

    def log(self, message: str, *, type: int, category=0, event_id=0, user_sid=None, raw_data=None):
        return ReportEvent(self.handle, type, category, event_id, user_sid, [message], raw_data)

    def info(self, message: str, **kwargs):
        return self.log(message, type=EVENTLOG_INFORMATION_TYPE, **kwargs)

    def warning(self, message: str, **kwargs):
        return self.log(message, type=EVENTLOG_WARNING_TYPE, **kwargs)

    def error(self, message: str, **kwargs):
        return self.log(message, type=EVENTLOG_ERROR_TYPE, **kwargs)
