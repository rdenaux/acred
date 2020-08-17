#
# Copyright (c) 2020 Expert System Iberia
#
"""Provides an IO layer for storing and retrieving `acred` related content.

In practice, at the moment, this means storing and retrieving acred
data-items from Solr.
"""
from acred import itnorm
from coinfoapy import credreview, solrio, ureview
from esiutils import dictu
import logging

logger = logging.getLogger(__name__)


def review_to_solr_update(review_ditems, target_schemas):
    """Convert a review data-item to a Solr update that matches the target schema

    :param review_ditem: a single Review data item or a list of such items

    :param target_schema: dict of solr data schemas. Keys are
      identifiers and values are solr schema dicts.

    :returns: one or more Solr update object matching the target schema that
      represents (the storable part of) the review_ditem

    :rtype: dict of solr update objects, keys are a subset of those in
      target_schemas, values are lists of solr update
      objects. Additionally, the response may contain special keys

      * `_already_stored`: containing review_ditems that are not included
        in any update because they were identified as already being stored.

      * `_missing_schema`: containing review_ditems whose type meant
        they could not be matched to any of the available target schemas.
    """
    if type(review_ditems) is list:
        # TODO: merge the individual results
        return [review_to_solr_update(ditem, target_schemas) for ditem in review_ditems]
    assert type(review_ditems) is dict
    cfg = {}
    review = itnorm.ensure_url(itnorm.ensure_ident(review_ditems, cfg), cfg)
    rev_str = '%s:%s' % (review.get('@type'), review.get('identifier'))
    item_index = itnorm.index_ident_tree(review, cfg)

    partition_schema = {k: v['ditemTypes'] for k, v in target_schemas.items()}
    parted_index = itnorm.partition_ident_index(item_index, partition_schema)

    result = {}
    for schema_id in target_schemas: 
        ditems_to_store = parted_index.get(schema_id, {})
        logger.info('Data item %s contains %s (sub)items matching schema %s' % (
            rev_str, len(ditems_to_store), schema_id))
        solr_schema = dictu.get_in(target_schemas, [schema_id, 'solr_schema'])
        trimmed_ditems = {
            ditem_id: solrio.trim_dict(ditem, ureview.review_stored_fields)
            for ditem_id, ditem in ditems_to_store.items()}
        result[schema_id] = [
            credreview.cred_review_to_solr_update_item(
                ditem, cfg, solr_schema=solr_schema)
            for ditem_id, ditem in trimmed_ditems.items()]

    logger.info('Input review %s contains %s items not matching any of the schemas %s. %s' % (
        rev_str, len(parted_index['_rest']), list(target_schemas.keys()),
        itnorm.build_index_type_histo(parted_index['_rest'])))

    return result
    

def solr_updates_to_reviews_index(solr_updates):
    """Reverse of `review_to_solr_update`

    :param solr_updates: list of solr update objects
    :returns: a data item index, i.e. a dict mapping from identifier
      strings to nested data items
    :rtype: dict
    """
    solr_doc_index = {doc['id']: doc for doc in solr_updates}
    ditem_index = {ident: credreview.solr_doc_to_review(doc)
                   for ident, doc in solr_doc_index.items()}
    return ditem_index
    
    
