from vizone import logging
from vizone.client import get_default_instance
from vizone.client import HTTPServerError, HTTPClientError
from vizone.resource.asset import get_asset_by_id, create_asset
from vizone.payload.asset import Item


def create_or_update_placeholder(id=None, metadata=None, client=None, log_id=-1):
    """
    Creates or Updates an Item with a given ``id``. Metadata updates will
    be retried three times if there are conflicts.

    Args:
        id (Optional[unicode]): An asset id or "site identity"
        metadata (Optional[vizone.vdf.Payload]): The metadata to update to
        client (Optional[vizone.client.Instance]): A Viz One client to use (None means the default)
        log_id (Optional[int): Log id to use in log prints

    Returns:
        vizone.payload.asset.Item: The updated or created Asset Entry
    """
    old_metadata = None
    client = client or get_default_instance()

    # Create or Update Placeholder
    try:
        asset = get_asset_by_id(id, headers={'X-Inline': 'describedby'}, client=client)
        old_metadata = asset.describedby_link.metadata
    except HTTPClientError:
        try:
            logging.info(u'(%i) Item %s does not exist, creating.', log_id, id)
            asset = Item(id=id)
            asset = create_asset(asset, client=client)
        except (HTTPClientError, HTTPServerError):
            logging.error(u'(%i) Could not create asset %s, skipping.', log_id, id)
            return
    
    # Update Metadata if needed
    if metadata is not None and metadata != old_metadata:
        logging.info(u'(%i) Updating metadata for asset %s.', log_id, asset.id)
        for _ in range(3):
            try:
                client.PUT(asset.describedby_link, metadata)
                break
            except HTTPServerError:
                logging.error(u'(%i) Could not update metadata for asset %s.', log_id, asset.id)
                return
            except HTTPClientError as e:
                logging.info(u'(%i) Asset Metadata update failed %s', log_id, str(e))
                if e.responstatus_code == 412:
                    logging.warn(u'(%i) Retrying...', log_id)
                    asset.parse(client.GET(asset.self_link))
                else:
                    break
    else:
        logging.info(u'(%i) Updating metadata for asset %s not needed.', log_id, asset.id)

    return asset


def delete_unmanaged_file(unmanaged_file, client=None, log_id=-1):
    """
    Delete an Unmanaged File from Viz One

    Args:
        unmanaged_file (vizone.payload.media.UnmanagedFile): The Unmanaged File to delete
        client (Optional[vizone.client.Instance]): A Viz One client to use (None means the default)
        log_id (Optional[int): Log id to use in log prints
    """
    logging.info(u'(%i) Deleting file %s.',
                 log_id, unmanaged_file.title)
    (client or get_default_instance()).DELETE(unmanaged_file.delete_link)


def import_unmanaged_file(asset, uri_list, client=None, log_id=-1):
    """
    Start an Unmanaged File import to a given Asset Entry

    Args:
        asset (vizone.payload.asset.Item): The Asset Entry to import to
        uri_list (vizone.urilist.UriList): A URI List containing the link to the media
        client (Optional[vizone.client.Instance]): A Viz One client to use (None means the default)
        log_id (Optional[int): Log id to use in log prints

    Returns:
        bool: True if successful, False on error
    """
    logging.info(u'(%i) Importing file %s to %s.',
                 log_id, uri_list.generate().strip(), asset.id)
    try:
        client.POST(asset.import_unmanaged_link, uri_list)
        return True
    except HTTPClientError:
        logging.error('(%i) Unable to import unmanaged file "%s" to asset %s',
                      log_id, uri_list.generate().strip(), asset.id)
        return False
