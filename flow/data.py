from threading import Lock
from vizone.client import HTTPClientError
from vizone.payload.dictionary import Dictionary
from vizone import logging


class MultiParser(object):
    Types = {"string", "integer", "float", "iso", "date", "time", "datetime", "dictionary"}
    DictionaryCache = {}
    CacheLock = Lock()

    def __init__(self, type="string", format=None, default_timezone="UTC", source=None):
        self.type = type
        self.format = format
        self.source = source
        self.default_timezone = default_timezone

        assert type in MultiParser.Types, "Converter type %s is not in %s" % (
                self.type, str(MultiParser.Types))

        if self.type in {"date", "time", "datetime"}:
            assert self.format, "Converter of type %s requires format" % (
                    self.type)

        if type is "dictionary":
            assert self.source, "Converter of type %s requires source" % (
                    self.type)

    def convert(self, raw_value, client):
        if raw_value is None or raw_value == "":
            return None
        if self.type == "string":
            return raw_value
        elif self.type == "integer":
            return int(raw_value)
        elif self.type == "float":
            return float(raw_value)
        elif self.type == "iso":
            return Timestamp(raw_value)
        elif self.type == "date":
            d = datetime.strptime(raw_value, self.format).date()
            t = Timestamp(d.isoformat())
            return t
        elif self.type == "time":
            d = datetime.strptime(raw_value, self.format).time()
            t = Timestamp(d.isoformat())
            return t
        elif self.type == "datetime":
            d = datetime.strptime(raw_value, self.format)
            t = Timestamp(d.isoformat())
            if not t.has_tz():
                t = t.assume(self.default_timezone)
            return t.utc()
        elif self.type == "dictionary":
            try:
                MultiParser.CacheLock.acquire()
                if self.source in MultiParser.DictionaryCache.keys():
                    dictionary = MultiParser.DictionaryCache[self.source]
                else:
                    try:
                        dictionary = Dictionary(client.GET(self.source))
                        MultiParser.DictionaryCache[self.source] = dictionary
                    except HTTPClientError:
                        raise ValueError("Bad dictionary link: %s" % self.source)
            finally:
                MultiParser.CacheLock.release()
            try:
                return [term for term in dictionary.entries if term.key == raw_value].pop(0)
            except IndexError:
                logging.error('Key "%s" missing in dictionary "%s".' %
                              (raw_value, self.source))

