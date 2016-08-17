import functools

from vizone import logging
from vizone.client import get_default_instance
from vizone.client import HTTPServerError, HTTPClientError
from vizone.resource.asset import get_asset_by_id, create_asset
from vizone.payload.asset import Item
from vizone.payload.common import AtomCategory
from vizone.payload.metadata import MetadataFormCollection
from vizone.vdf import Model


class Retry(Exception):
    """
    Exception that can be raised within a retry_on_conflict context to
    retry prematurely.
    """
    pass


def retry_on_conflict(max_retries=3):
    """
    Decorator that can wrap a function or method and retry it upon
    a conflict exception.

    Example:

    .. code-block:: python
        
        @retry_on_conflict(max_retries=3)
        def my_function(self, entry, conflict=False):

            # If there was a conflict, the entry needs to be refetched
            if conflict:
                entry.parse(self.client.GET(entry.self_link))

            # Do the operations
            self.client.PUT(entry.edit_link, entry)

    Note that:
    
    - Any argument will be reused as it, with changes.

    - You can raise a ``Retry`` exception to retry for other reasons than
      a 409 Conflict.
    """
    class RetryOnConflict(object):
        def __init__(self, func):
            self.func = func
        
        def __call__(self, *args, **kwargs):
            for retry in range(max_retries):
                try:
                    logging.debug(u'RetryOnConflict, attempt %i of %i...',
                                 retry + 1, max_retries)

                    kwargs['conflict'] = retry > 0
                    return (self.func)(*args, **kwargs)

                # If we have a conflict, retry the entire operation
                except HTTPClientError as e:
                    logging.warn(u'Update failed %s', str(e))
                    if e.response.status_code == 409: # etag violation
                        logging.warn(u'Retrying...')
                    else:
                        break

                except Retry as e:
                    logging.warn(u'Retrying...')

        def __repr__(self):
            return self.func.__doc__

        def __get__(self, obj, objtype):
            return functools.partial(self.__call__, obj)

    return RetryOnConflict


def create_or_update_asset(
        id=None,
        metadata=None,
        acl=None,
        mediaacl=None,
        tags=None,
        materialtype=None,
        category=None,
        rightscode=None,
        client=None):
    """
    Creates or Updates an Item with a given ``id``. Metadata updates will
    be retried three times if there are conflicts.

    Args:
        id (Optional[unicode]): An asset id or "site identity"
        metadata (Optional[vizone.vdf.Payload]): The metadata to update to. Can be a dict with a 'form' field too.
        acl (Optional[vizone.vizone.payload.user_group.Acl]): Specify a ACL when creating the Asset
        mediaacl (Optional[vizone.vizone.payload.user_group.Acl]): Specify a Media ACL when creating the Asset
        tags (Optional[dict]): scheme => term dictionary for custom tags when creating the Asset
        materialtype (Optional[unicode]): Set the Material Type to this when creating the Asset
        category (Optional[unicode]): Set the Category to this when creating the Asset
        rightscode (Optional[unicode]): Set the Rights Code to this when creating the Asset
        client (Optional[vizone.client.Instance]): A Viz One client to use (None means the default)

    Returns:
        vizone.payload.asset.Item: The updated or created Asset Entry
    """
    old_payload = None
    client = client or get_default_instance()

    # Create or Update Placeholder
    try:
        asset = get_asset_by_id(id, headers={'X-Inline': 'describedby'}, client=client)
        old_payload = asset.describedby_link.metadata
    except HTTPClientError:
        try:
            logging.info(u'Item %s does not exist, creating.', id)
            asset = Item(id=id)

            if acl:
                asset.acl = acl
            if mediaacl:
                asset.mediaacl = mediaacl
            if materialtype:
                asset.materialtype = materialtype
            if category:
                asset.category = category
            if rightscode:
                asset.rightscode = rightscode
            if tags:
                for scheme, term in sorted(tags.items()):
                    asset.keywords.append(
                        AtomCategory(scheme=scheme, term=term)
                    )

            asset = create_asset(asset, client=client)
        except (HTTPClientError, HTTPServerError):
            logging.error(u'Could not create asset %s, skipping.', id)
            return
    
    # Create payload if metadata is a dict
    if type(metadata) is dict:
        form = metadata.pop('form')
        if old_payload is None:
            models = MetadataFormCollection(client.GET(asset.models_link))
            model_link = [model.self_link for model in models.entries if model.name == form][0]
            model = Model(client.GET(model_link))
            payload = model.to_payload()
        else:
            payload = old_payload
        for name, value in metadata.items():
            payload.set(name, value)
    else:
        payload = metadata

    # Update Metadata if needed
    if payload is not None and payload != old_payload:
        logging.info(u'Updating metadata for asset %s.', asset.id)
        for _ in range(3):
            try:
                asset.describedby_link.metadata = client.PUT(asset.describedby_link, payload)
                break
            except HTTPServerError:
                logging.error(u'Could not update metadata for asset %s.', asset.id)
                return
            except HTTPClientError as e:
                logging.info(u'Asset Metadata update failed %s', str(e))
                if e.responstatus_code == 412:
                    logging.warn(u'Retrying...')
                    asset.parse(client.GET(asset.self_link))
                else:
                    break
    else:
        logging.info(u'Updating metadata for asset %s not needed.', asset.id)

    return asset


def delete_unmanaged_file(unmanaged_file, client=None):
    """
    Delete an Unmanaged File from Viz One

    Args:
        unmanaged_file (vizone.payload.media.UnmanagedFile): The Unmanaged File to delete
        client (Optional[vizone.client.Instance]): A Viz One client to use (None means the default)
    """
    logging.info(u'Deleting file %s.', unmanaged_file.title)
    (client or get_default_instance()).DELETE(unmanaged_file.delete_link)


def import_unmanaged_file(asset, uri_list, client=None):
    """
    Start an Unmanaged File import to a given Asset Entry

    Args:
        asset (vizone.payload.asset.Item): The Asset Entry to import to
        uri_list (vizone.urilist.UriList): A URI List containing the link to the media
        client (Optional[vizone.client.Instance]): A Viz One client to use (None means the default)

    Returns:
        bool: True if successful, False on error
    """
    logging.info(u'Importing file %s to %s.',
                 uri_list.generate().strip(), asset.id)
    try:
        client.POST(asset.import_unmanaged_link, uri_list)
        return True
    except HTTPClientError:
        logging.error('Unable to import unmanaged file "%s" to asset %s',
                      uri_list.generate().strip(), asset.id)
        return False
