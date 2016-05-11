from threading import Lock
from vizone.client import HTTPClientError
from vizone.payload.dictionary import Dictionary
from vizone import logging


class MultiParser(object):
    """
    A value parser that converts various data formats into Python and Viz One
    entities, including:

    - ``unicode`` (default)
    - ``int``
    - ``float``
    - ``iso8601`` (timestamp)
    - ``date`` (date with configurable format)
    - ``time`` (time with configurable format)
    - ``datetime`` (date + time with configurable format)
    - ``dictionary`` (dictionary term with given source reference)

    The intended use is for putting the resulting object as value into a
    VDF Payload. 
    
    Example:

    .. code-block:: python

        from flow.data import MultiParser

        mp = MultiParser(type='date', format='%d/%m')
        result = mp.convert('4/12')

    For a more thourough example using the MultiParser together with configuration,
    please check out :class:`xmlimport.XmlImport`.

    For more information about date and time parsing syntax, please refer to
    https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior

    Args:
        type (str): ``string|integer|float|iso|date|time|datetime|dictionary``
        format (str): format string for parseing ``date``, ``time`` and ``datetime``
        default_timezone (str): default time zone only used fore ``datetime``
        source (str): url do ``dictionary``, should be an Atom-based feed
    """
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
        """
        Perform conversion configured when contructing the object.

        Args:
            raw_value (unicode): The raw string to parse
            client (vizone.client.Instance): The HTTP client to use when looking up dictionary terms.

        Returns:
            object
        """
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

