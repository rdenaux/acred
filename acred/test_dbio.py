#
# Copyright (c) 2020 Expert System Iberia
#
"""Tests the dbio.py module

"""
from acred import dbio, itnorm
from esiutils import dictu
import json

def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

aggqsentReview01 = read_json('test/AggQSentCredReview/Clef18_Train_Task2-English-1st_Presidential1.json')
solr_schema_review = read_json('test/solr_schema_review.json')


def test_review_to_solr_update_01():
    target_schemas = {'review': {'ditemTypes': ['CredibilityReview', 'SentSimilarityReview',
                                                'SentPolarSimilarityReview', 'SentStanceReview'],
                                 'solr_schema': solr_schema_review['schema']}}
    solr_update = dbio.review_to_solr_update(aggqsentReview01, target_schemas)
    assert type(solr_update) is dict
    assert set(['review']) == set(list(solr_update.keys()))
    rev_updates = solr_update['review']
    assert type(rev_updates) is list
    assert 62 == len(rev_updates) # 22 credreviews, 
    updates_by_url = sorted(rev_updates, key=lambda r: r['url'])
    # with open('test/reviewSolrDocs/Clef18_Train_Task2-English-1st_Presidential1.json', 'w') as f:
    #     json.dump(updates_by_url, f, indent=2)
    assert set(['@context', '@type', #'additionalType',
                'author.@context', 'author.@type',
                'author.additionalType', 'author.name', 'author.url',
                'dateCreated', 'id', 'itemReviewed.@context',
                'itemReviewed.@type', 'itemReviewed.text',
                #'itemReviewed.url','reviewAspect',
                'reviewRating.@type',
                #'reviewRating.additionalType',
                'reviewRating.reviewAspect', 'reviewRating.url',
                #'reviewRating.ratingExplanation',
                'url', 'reviewRating.ratingValue_f']) == set(updates_by_url[0].keys())

def test_review_to_solr_update_roundtrip_01():
    # context
    target_schemas = {'review': {'ditemTypes': ['CredibilityReview', 'SentSimilarityReview',
                                                'SentPolarSimilarityReview', 'SentStanceReview'],
                                 'solr_schema': solr_schema_review['schema']}}
    cfg = {}

    # setup: make sure we have idents and url for all data items
    review = itnorm.ensure_url(itnorm.ensure_ident(aggqsentReview01, cfg), cfg)
    rev_id = review.get('identifier')

    # this is the index for the review before converting to solr schema 
    expected_index = itnorm.index_ident_tree(review, cfg)

    # phase1: convert to solr, this is tested in another unit test
    solr_update = dbio.review_to_solr_update(review, target_schemas)
    rev_updates = solr_update['review'] # list of solr docs

    # phase2: roundtrip, try to reconstruct the expected index based on the
    #  solr docs only
    recon_rev_index = dbio.solr_updates_to_reviews_index(rev_updates)
    assert 31 == len(recon_rev_index)
    assert rev_id in recon_rev_index # the main review id is included
    
    for review_id in recon_rev_index:
        assert_reconstructed_review(recon_rev_index[review_id], expected_index[review_id], cfg)

def assert_reconstructed_review(recon_rev, original_review, cfg):
    rev_type = original_review['@type']
    expected_fields = list(original_review.keys())
    if rev_type == 'WebSiteCredReview':
        filtered_fields = ['timings', 'isBasedOn_assessments', 'isBasedOn']
        expected_fields = [f for f in expected_fields if f not in filtered_fields]
    assert set(list(recon_rev.keys())) == set(expected_fields), original_review['@type']
    expected_fields = ['@context', '@type', 'additionalType', 'author', 'dateCreated',
                       'isBasedOn', 'itemReviewed', 'reviewRating', 'identifier', 'url']
    full_retrieval_fields = ['@context', '@type', 'additionalType', 'dateCreated',
                             'reviewRating', 'identifier', 'url']
    for k in full_retrieval_fields:
        if k in original_review:
            if k == 'reviewRating' and '@context' in original_review[k] and '@context' not in recon_rev[k]:
                recon_rev[k]['@context'] = original_review[k]['@context']
            assert itnorm.ensure_ident(recon_rev[k], cfg) == original_review[k], '%s in %s' % (
                k, original_review['identifier'])

    partial_retrieval_fields = {
        'author': ['@context', '@type', 'additionalType', 'name', 'url'],
        'isBasedOn': ['url'],
        'itemReviewed': ['@context', '@type', 'text', 'name', 'url']}
    for field, expected_fields in partial_retrieval_fields.items():
        if field not in original_review:
            continue
        val = original_review[field]
        tval = type(val)
        if tval is list:
            expected_value = [dictu.select_keys(it, expected_fields) for it in val]
        elif tval is dict:
            expected_value = dictu.select_keys(val, expected_fields)
            assert recon_rev[field] == expected_value, '%s in %s' % (field, recon_rev['identifier'])
        else:
            raise ValueError('Field %s is not a list or a dict %s' % (
                field, tval))    
    
