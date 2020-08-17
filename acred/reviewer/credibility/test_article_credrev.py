#
# Copyright (c) 2020 Expert System Iberia
#
"""
Unit Tests for the dbsent_credrev
"""
import pytest
import json
import copy
from acred.reviewer.credibility import article_credrev

def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def integration_test_analyzed_doc_01():
    url_doc = read_json('test/url_doc_8.json')
    cfg = {
        'ciapi_gsl_id': 10021140,
        'ciapi_sa_base_url': 'https://192.168.192.163:9322'
    }
    adoc = article_credrev.analyzed_doc(url_doc, {})
    assert 'claims_content' in adoc

def integration_test_select_claims_in_doc_01():
    url_doc = read_json('test/url_doc_8.json')
    cfg = {
        'ciapi_gsl_id': 10021140,
        'ciapi_sa_base_url': 'https://192.168.192.163:9322'
    }
    adoc = article_credrev.analyzed_doc(url_doc, {})
    claims = article_credrev.select_claims_in_doc(adoc, cfg)
    assert len(claims) == 5
    



