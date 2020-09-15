#
# Copyright (c) 2019 Expert System Iberia
#
"""
Provides functionality to search and predict claim credibility based on a
 database of claims/sentences
"""
import logging
import time
import requests
import json
from acredapi import config, cache
import numpy as np
from acredapi.InvalidUsage import InvalidUsage
from acred import content
from acred.reviewer.credibility import website_credrev
from esiutils import citimings, isodate, dictu


# Setup
logger = logging.getLogger(__name__)
ci_context = 'http://coinform.eu'


def stub_claim_cred_pred(claim):
    return {
        'claim': claim,
        'credibility': 0.5,
        'confidence': 0.1,
        'related_claims': {
            'reviewed-claims': [],
            'fact-checker-sentences': [],
            'credible-pub-sentences': [],
            'non-credible-pub-sentences': []
        },
        'explanation': 'stub explanation, credibility prediction not implemented yet.'
    }


def predict_claim_credibility(claim):  # noqa: E501
    """analyses a claim to predict its credibility

    Analyses the input claim and compares it to existing claims/statements in the database. Based on the result, it produces a credibility score with optional details explaining what the score is based on and linking to similar claims.  # noqa: E501

    :param claim: required string. This should be a sentence or claim. If multiple sentences are passed, this will result in multiple predictions for the individual claims.
    :type claim: str

    :rtype: List[ClaimCredibilityPrediction]
    """
    if type(claim) == list:
        return [predict_claim_credibility(c) for c in claim]
    if claim is None:
        raise InvalidUsage("Claim is mandatory", status_code=400)
    return stub_claim_cred_pred(claim)


def stub_related_sentence():
    return {
        'sentence': 'Migration Watch UK estimates that about 3.1 million migrants arrived and a further 2.3 million were born in Britain between 2001 and 2016',
        'similarity': 0.5,
        'doc_url': 'https://www.expressen.se/nyheter/val-2018/klimatet-huvudfragan-i-forsta-partiledardebatten',
        'lang_orig': 'sv',
        'published_date': '2019-05-07T15:40:46.791Z',
        'domain': 'africacheck.org'
    }


def stub_related_claimReview():
    return {
        'claimReviewed': 'We are contributing to the national government in excess of KSh49 billion in taxes annually.',
        'similarity': 0.5,
        'url': 'https://africacheck.org/_on-a-year-in-import-tax/',
        'fact-checker': 'Africa Check',
        'altName': 'Incorrect',
        'lang_orig': 'sv',
        'published_date': '2019-05-07T15:40:46.791Z',
        'domain': 'africacheck.org'
    }


now_ms = lambda: int(round(time.time() * 1000))


@cache.memoize(timeout=500)
def search_semantic_vecspace(q_claims, topn=10):
    url = neural_index_url + '/search_semantic_vecspace'
    req = {'query_sentences': q_claims,
           'topn' : topn,
           'provenance': True}
    resp = requests.post(url, json=req, verify=False)
    logger.info("Response from %s %s" % (url, resp))
    jresp = resp.json()
    return jresp['similarities'], jresp['claim_ids'], jresp.get('author')


def simReviewer():
    url = neural_index_url + '/sim_reviewer'
    resp = requests.get(url, verify=False)
    logger.info("Response from %s %s" % (url, resp))
    jresp = resp.json()
    return jresp


def predict_stances(qclaim_doc_bodies):
    url = stance_pred_url + '/predict_stance'
    req = qclaim_doc_bodies
    resp = requests.post(url, json=req, verify=False)
    logger.info("Response from %s %s" % (url, resp))
    jresp = resp.json()
    return jresp['labels'], jresp['confidences'], dictu.get_in(
        jresp, ['meta', 'model_info'])


def stancePredictor():
    url = stance_pred_url + '/stance_predictor'
    resp = requests.get(url, verify=False)
    logger.info("Response from %s %s" % (url, resp))
    jresp = resp.json()
    return jresp


def do_add_stance_labels(claim_sim_results, sim_threshold=0.7, max_len=128):
    start = citimings.start()

    def trim(s, max_len):
        s_toks = s.split(' ')
        if len(s_toks) > max_len:
            return ' '.join(s_toks[:max_len])
        else:
            return s
    
    stance_reqs = []
    for cresult in claim_sim_results:
        q_claim = cresult['q_claim']
        q_claim_toks = q_claim.split(' ')
        if len(q_claim_toks) > (2*max_len/3):
            logger.warning('Skip stance_pred: q_claim is too large %d ' % (
                len(q_claim_toks)))
            continue
        bods, rs_targets = [], []
        for rs in cresult['results']:
            if rs['similarity'] < sim_threshold:
                continue
            # docbod = rs.get('doc_content', None)
            # if docbod is not None:
            #     bods.append(trim(docbod, max_len))
            #     rs_targets.append({"rs": rs,
            #                        'field': 'doc_stance'})
            sent = rs.get('sentence', None)
            if sent is not None:
                bods.append(sent)
                rs_targets.append({'rs': rs,
                                   'field': 'sent_stance'})
        if len(bods) > 0:
            stance_reqs.append({
                'qclaim': q_claim,
                'doc_bodies': bods,
                'rs_targets': rs_targets})

    if len(stance_reqs) == 0:
        return claim_sim_results, citimings.timing(
            'predict_stances', start)

    labels, confs, stanceRev = predict_stances(
        # don't send the rs_targets to server
        [dictu.select_keys(sr, ['qclaim', 'doc_bodies'])
         for sr in stance_reqs])

    for csr in claim_sim_results:
        csr['stanceReviewer'] = stanceRev
    stance_docs_t = citimings.timing('doc_stance_pred', start)
    logger.info("Predicted stances %s with scores %s" % (labels, confs))

    rs_targets = [rs_target for req in stance_reqs
                  for rs_target in req['rs_targets']]
    assert len(rs_targets) == len(labels)
    assert len(confs) == len(labels)
    for rs_target, label, conf in zip(rs_targets, labels, confs):
        rs = rs_target['rs']
        field = rs_target['field']
        rs[field] = label
        rs['%s_confidence' % field] = conf


    return claim_sim_results, citimings.timing(
        'predict_stances', start,
        [stance_docs_t])


def add_stance_detection(claim_sim_results, sim_threshold=0.7):
    """Adds `doc_content` and `*_stance` fields to the input sim_results

    :param claim_sim_results: list of ClaimSimilarityResults
    :param sim_threshold: only perform stance detection for match results
      that are more similar than this value. Useful since stance detection is
      fairly slow.
    :returns: a modified `claim_sim_results` and timings
    :rtype: tuple
    """
    start = citimings.start()

    sub_ts = []
    start2 = citimings.start()
    result, stance_timing = do_add_stance_labels(
        claim_sim_results, sim_threshold=sim_threshold)
    sub_ts.append(stance_timing)
    stance_pred_t = citimings.timing('stance_pred', start2, sub_ts)
    return result, stance_pred_t

    

def retrieve_result_claims(claim_ids, q_claims, topn):
    claim_id_set = set(np.array(claim_ids).flatten())
    logger.info("Top %d claims for %d query sents resulted in %d claims" % (
        topn, len(q_claims), len(claim_id_set)))

    start = citimings.start()
    dbdocs = find_in_dbs(dbs=[preCrawled_sents_db, claimReviewed_sents_db], q_ids=list(claim_id_set))
    q_resp = {'response': {'docs': dbdocs}} 
    claim_retrieve_t = citimings.timing('retrieve_claims', start)
    return q_resp, claim_retrieve_t

def find_in_dbs(dbs, q_ids):
    if type(dbs) is list:
        result = []
        for db in dbs:
            result.extend(find_in_dbs(db, q_ids))
        return result
    # single DB
    assert type(dbs) is dict
    assert dbs['@type'] == 'InMemoryClaimDB'
    assert type(q_ids) is list
    if len(q_ids) == 0:
        return []
    db = dbs
    doc_idxs = [db['id2doc_index'].get(q_id) for q_id in q_ids]
    doc_idxs = [idx for idx in doc_idxs if idx is not None]
    return [db['docs'][i] for i in doc_idxs]

def search_claim_bots():
    """Returns a map describing the bots involved in `search_claim`

    :returns: a map describing the bots involved in `search_claim`
    :rtype: dict
    """
    start = citimings.start()
    bots = {
        'simReviewer': simReviewer(), # includes the sentence encoder bot!
        'stancePred': stancePredictor()}
    timing = citimings.timing('search_claim_bots', start)
    return {
        'results': [], # no similar sentence results
        'bots': bots,
        'resultsHeader': {
            'QTime': timing['total_ms'],
            'timings': timing,
            'params': {}}}    

@cache.memoize(timeout=500)
def search_claim(q_claim):
    """finds similar claims or sentences in a claim database

    Finding similar claims or sentences in the co-inform claim database # noqa: E501

    :param q_claim: This should be an English sentence or claim. Multiple sentences are not allowed.
    :type q_claim: str
    :rtype: dict
    """
    if type(q_claim) is str:
        q_claims = [q_claim]
    if type(q_claim) is list:
        q_claims = q_claim
    if q_claim is None:
        raise InvalidUsage("Claim is mandatory")
    start = citimings.start()
    logger.info('Searching semantic vector space for %s claim(s)' % len(
        q_claims))
    topn = 5
    preds, claim_ids, simReviewer = search_semantic_vecspace(q_claims, topn=topn)
    search_semspace_t = citimings.timing('search_semantic_vecspace', start)

    assert len(preds) == len(claim_ids)
    assert len(q_claims) == len(preds)
    q_resp, claim_retrieve_t = retrieve_result_claims(claim_ids, q_claims, topn)

    start3 = citimings.start()
    results, sub_build_ts = [], []
    for i in range(len(q_claims)):
        start4 = citimings.start()
        claim_id2pred = {idx: float(pred) for idx, pred in zip(
            claim_ids[i], preds[i])}
        relsents, sub_ts = q_resp_to_related_sent(
            q_resp, claim_id2pred)
        qclaim = q_claims[i]
        results.append({
            '@context': ci_context,
            '@type': 'SemanticClaimSimilarityResult',
            'dateCreated': isodate.now_utc_timestamp(),
            'q_claim': qclaim,
            'simReviewer': simReviewer,
            'results': relsents})
        sub_build_ts.append(citimings.timing('build_result', start4, sub_ts))
    result_build_t = citimings.timing('build_results', start3, sub_build_ts)

    results, stance_pred_t = add_stance_detection(
        results, sim_threshold=stance_min_sim_threshold)

    timing = citimings.timing(
        'search_claim', start,
        [search_semspace_t, claim_retrieve_t,
         result_build_t, stance_pred_t])
    return {
        'results': results,
        'resultsHeader': {
            'QTime': timing['total_ms'],
            'timings': timing,
            'params': {
                'claim': q_claim
            }}}


def q_resp_to_related_sent(q_resp, claimid2pred):
    start = citimings.start()
    docs = q_resp['response']['docs']

    def dbdoc2_resp_doc(doc):
        return as_related_sent_or_claimReview(doc, claimid2pred)
    
    # we are only interested in documents that appear in claimid2pred
    # otherwise these may be results for a differnt q_claim
    docs4claim = [doc for doc in docs if doc['id'] in claimid2pred]
    logger.info("Found %d (of %d) claims" % (
        len(docs4claim), len(claimid2pred)))
    if len(claimid2pred) != len(docs4claim):
        logger.warn("Expecting %d docs, but found %d.\n%s" % (
            len(claimid2pred), len(docs4claim), str(claimid2pred)))
    result_and_timings = [dbdoc2_resp_doc(doc) for doc in docs4claim]
    sub_ts = [rt[1] for rt in result_and_timings]
    result = [rt[0] for rt in result_and_timings]
    result = sorted(result, key=lambda doc: doc['similarity'], reverse=True)
    return result, citimings.timing('doc_as_relsent', start, sub_ts)



def as_related_sent_or_claimReview(db_claim_doc, claimid2pred):
    start = citimings.start()
    multival_separator = ','
    doc_urls = db_claim_doc.get('urls_ss', '').split(multival_separator)
    domains = db_claim_doc.get('domains_ss', '').split(multival_separator)
    domain = None
    if len(domains) == 0:
        # logger.warn("Claim doc is missing domains_ss")
        if len(doc_urls) > 0:
            domain = content.domain_from_url(doc_urls[0])
    else:
        domain = domains[0]

    return {
        '@context': ci_context,
        '@type': 'SimilarSent',
        'sentence': db_claim_doc['content_t'],
        'similarity': claimid2pred.get(db_claim_doc['id'], 0.5),
        'doc_url': None if len(doc_urls) == 0 else doc_urls[0],
        'appearance': doc_urls,
        'lang_orig': db_claim_doc.get('lang_s', None),
        'published_date': db_claim_doc.get(
            'published_dts', [None])[0] or db_claim_doc.get('schema_org_cr_itemReviewed_datePublished_tdt', None),
        'domain': domain,
        'claimReview': lookup_claimReview_url(db_claim_doc['schema_org_cr_url'], claimReview_db)
    }, citimings.timing('as_related_sent', start,
                        [])


def read_sents_db_from_csv(path):
    import csv
    with open(path) as csv_file:
        reader = csv.reader(csv_file)
        field_names = None
        db = {
            '@type': 'InMemoryClaimDB',
            'path': path,
            'field_names': field_names,
            'docs': [],
        }
        try:
            for row in reader:
                if field_names is None:
                    field_names = row
                    db['field_names'] = field_names
                    continue
                doc = {f: v for f, v in zip(field_names, row)}
                db['docs'].append(doc)
            db['id2doc_index'] = {doc['id']: idx
                                  for idx, doc in enumerate(db['docs'])}
        except csv.Error as e:
            logger.error('Failed to load %s, line %s: %s' % (path, reader.line_num, e), e)
        logger.info('Read doc DB from %s with fields %s, %s docs and %s ids' % (
            db['path'], db['field_names'], len(db['docs']), len(db['id2doc_index'])))
        return db

def read_claimReview_db_from_jsonl(path):
    db = {
        '@type': 'InMemoryClaimReviewDB',
        'path': path,
        'docs': []
    }
    with open(path) as jsonl_file:
        db['docs'] = [json.loads(json_str) for json_str in jsonl_file]
    db['url2doc_index'] = {doc['url']: idx
                           for idx, doc in enumerate(db['docs'])}
    return db

def lookup_claimReview_url(url, claimReview_db):
    """Looks up a URL for a ClaimReview in our DB

    :param url: str URL value for a ClaimReview
    :param claimReview_db: a ClaimReview database
    :returns: a dict
    :rtype: dict
    """
    assert type(claimReview_db) is dict, '%s' % (type(claimReview_db))
    assert claimReview_db.get('@type') == 'InMemoryClaimReviewDB'
    idx = claimReview_db.get('url2doc_index', {}).get(url, None)
    if idx:
        return claimReview_db['docs'][idx]
    else:
        return None

neural_index_url = config['acredapi']['neuralindex_url']
stance_pred_url = config['acredapi']['stance_pred_url']
stance_min_sim_threshold = float(config['acredapi'].get('stance_min_sim_threshold', 0.75))
claimReview_db = read_claimReview_db_from_jsonl(config['acredapi']['claimReview_db_jsonl'])
preCrawled_sents_db = read_sents_db_from_csv(config['acredapi']['sentences_extracted_db_csv'])
claimReviewed_sents_db = read_sents_db_from_csv(config['acredapi']['sentences_from_ClaimReviews_db_csv'])
