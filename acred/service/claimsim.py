#
# Copyright (c) 2020 Expert System Iberia
#
"""Provides a claim similarity service needed by some reviewers.

This is basically an optimisation: instead of having to perform
similarity search for each individual sentence, this performs claim
similarity and stance detection for a batch.
"""
import requests
import logging
from esiutils import dictu


logger = logging.getLogger(__name__)


def read_claim_search_req_params(cfg):
    claim_search_url = cfg.get(
        'acred_pred_claim_search_url',
        'http://localhost:8070/test/api/v1/claim/internal-search')
    auth_user = cfg.get('acred_search_auth_user', 'testuser')
    auth_pass = cfg.get('acred_search_auth_pwrd', 'testpass')
    if auth_user is None and auth_pass is None:
        auth = None
    else:
        auth = requests.auth.HTTPBasicAuth(auth_user, auth_pass)
    search_verify = cfg.get('acred_search_verify', False)
    return claim_search_url, auth, search_verify
    

def find_related_sentences(sents, cfg):
    """Retrieves a `SemanticClaimSimilarityResult` for each query sentence

    :param sents: a list of query sentences (just the sentence text, **not** 
      the object)
    :param cfg: configuration options
    :returns: a list of `SemanticClaimSimilarityResult` instances, this list 
      is aligned with the input `sents`. If empty, something went wrong with 
      the retrieval.
    :rtype: list
    """
    if sents is None or len(sents) == 0:
        return []
    claim_search_url, auth, search_verify = read_claim_search_req_params(cfg)
    req = {
        'claims': sents
    }
    logger.info("Finding related sentences from %s" % claim_search_url)
    resp = requests.post(claim_search_url,
                         json=req,
                         verify=search_verify, auth=auth)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error('Failed to find related sentences: ' + str(e))
        return []

    respd = resp.json()
    results = respd.get('results')
    if results is None:
        logger.error("No related sentences?" + list(respd.keys()))
        return []
    return [rel_sents for rel_sents in results]


def semSentSimReviewer(cfg):
    if 'dev_mock_semSentSimReviewer' in cfg:
        return cfg['dev_mock_semSentSimReviewer']
    claim_search_url, auth, search_verify = read_claim_search_req_params(cfg)
    resp = requests.post(claim_search_url, json={}, verify=search_verify, auth=auth)
    resp.raise_for_status()
    return dictu.get_in(resp.json(), ['bots', 'simReviewer'])


def semSentenceEncoder(cfg):
    if 'dev_mock_semSentenceEncoder' in cfg:
        return cfg['dev_mock_semSentenceEncoder']
    claim_search_url, auth, search_verify = read_claim_search_req_params(cfg)
    resp = requests.post(claim_search_url, json={}, verify=search_verify, auth=auth)
    resp.raise_for_status()
    return dictu.get_in(resp.json(), ['bots', 'simReviewer', 'isBasedOn'])[0]

def stancePredictor(cfg):
    if 'dev_mock_stancePredictor' in cfg:
        return cfg['dev_mock_stancePredictor']
    claim_search_url, auth, search_verify = read_claim_search_req_params(cfg)
    resp = requests.post(claim_search_url, json={}, verify=search_verify, auth=auth)
    resp.raise_for_status()
    return dictu.get_in(resp.json(), ['bots', 'stancePred'])

