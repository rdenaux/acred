#
# Copyright (c) 2020 Expert System Iberia
#
"""Implements a factcheckability reviewer based on the ClaimBuster API
"""

def review(item, config):
    """Reviews the incoming item and returns 

    :param item: a single item or a list of items, in this case the 
      items must be `Sentence` instances.
    :param config: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: dict or list of dict
    """
    raise NotImplemented()
