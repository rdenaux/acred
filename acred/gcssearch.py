#
# Copyright (c) 2020 Expert System Iberia
#
"""Provide search functionality to find Ground Credibility Signals
"""

def find_preindexed_doc_by_url(url, collections):
    """Searches the database of pre-indexed documents by URL

    :param url: the url of the pre-indexed document
    :param collections: list of collection ids where we should try to
      find the documents.
    :returns: a pre-indexed document, a dict
      representing the document, extracted claims will be in field 
      'claims_content'. 
    :rtype: dict or None
    """
    return None # FIXME: implement by reading first from exported CSVs


