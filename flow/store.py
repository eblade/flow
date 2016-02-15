import json


class Store(object):
    """
    A Store is a centralizer store based on the Client Config API.
    """
    def __init__(self, appname, client):
        """
        Store contructor is not lightweight, so you might want to reuse the instance.
        It only works with dicts for values and they are stored as JSON strings on
        the server side.

        Args:
            appname (unicode): Name of the application, used in the API calls
            client (vizone.client.Instance): Viz One client to use for calls
        """
        self._appname = appname or ''  # application is optional
        self._client = client

        collection = client.servicedoc.get_collection_by_keyword('client-config')
        self._resolve = collection.get_resolve_by_id('client-config')
    
    def get(self, key):
        """
        Get the value of a certain key for the object's application.

        Args:
            key (unicode): The key used for storage

        Returns:
            dict: The storede value or ``None``
        """
        subs = {'vizid:application': self._appname}
        resolve = self._resolve

        response = self._client.GET(resolve.make_url(key, subs), check_status=False)
        if response.status_code == 404:
            return None
        elif response.status_code >= 500:
            logging.log("HTTP Server Error %i" % response.status_code, response.content, 'xml', debug=False)
            raise HTTPServerError(response)
        elif response.status_code >= 400:
            logging.log("HTTP Client Error %i" % response.status_code, response.content, 'xml', debug=False)
            raise HTTPClientError(response)

        if response.content != '':
            return json.loads(response.content)
        else:
            return None

    def put(self, key, value):
        """
        Put a ``value`` under a ``key`` for the object's application.

        Args:
            key (unicode): The key used for storage
            value (dict): The data to store, as a dict

        Returns:
            dict: The storede value is returned
        """
        value = json.dumps(value)
        subs = {'vizid:application': self._appname}
        resolve = self._resolve

        self._client.PUT(resolve.make_url(key, subs), value, {'Content-Type': 'application/octet-stream'})
        return value

    def delete(self, key):
        """
        Delete the stored ``value`` under a ``key`` for the object's application.

        Args:
            key (unicode): The key to delete
        """
        subs = {'vizid:application': self._appname}
        resolve = self._resolve

        self._client.DELETE(resolve.make_url(key, subs))
