#
# Copyright (c) 2019 Expert System Iberia
#
"""
tweetrelsents: utility for extracting relevant sentences in
  or linked from  a tweet:
  1. extracts sentences from the text of a tweet
  2. extracts urls mentioned in a tweet, retrieves and processes with ciapi
"""
import sys
import logging
import re
import requests
import json
import argparse
from semantic_analyzer import url_scraper
from semantic_analyzer import analyzer as semalizer
from esiutils import citimings


logger = logging.getLogger(__name__)

gcssearch_available = False
try:
    from acred import gcssearch
    gcssearch_available = True
    logger.info("Successfully loaded gcssearch %s" % gcssearch_available)
except ImportError:
    logger.warn('Failed to import gcssearch. Tweetrelsents not colocated?')


def find_url(string):
    url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string) 
    return url


def build_in_tweet_info(tweetID, sent_list, cfg):
    in_tweet = []
    for sent in sent_list:
        sentence_json = {
            'sentence_type': cfg.get('sentence_type', "full_sentence"),
            'in_tweet': tweetID,
            'extractor': cfg.get('sentence_extractor', 'nltk'),
            'text': sent
        }
        in_tweet.append(sentence_json)
    return in_tweet


def _find_preindexed_docs_by_id_via_ws(doc_url, cfg):
    # was find_coinform_docs_by_id(doc_url, cfg):
    collections_solr = cfg.get(
        'relsents_in_colls',
        ['pilot-se', 'pilot-gr', 'pilot-at', 'factcheckers', 'fc-dev'])
    auth_user = cfg.get('relsents_search_auth_user', 'testuser')
    auth_pass = cfg.get('relsents_search_auth_pwrd', 'testpass')
    if auth_user is None and auth_pass is None:
        auth = None
    else:
        auth = requests.auth.HTTPBasicAuth(auth_user, auth_pass)
    search_url = cfg.get('relsents_search_url',
                         'http://localhost:8070/test/api/v1/search')
    # search_url = 'https://coinform.expertsystemcustomer.com/cc/api/v1/search'
    search_verify = cfg.get('relsents_search_verify', False)
    for coll in collections_solr:
        # FIXME: this fails often as it's rate-limited, we'd be better off
        #  calling this directly, or adding an internal-search version
        resp = requests.get(
            '%s?collection=%s&expand_claims=true&q_id=%s' % (
                search_url, coll, doc_url),
            verify=search_verify, auth=auth)
        if resp.ok:
            try:
                solr_json = resp.json()
                docs = solr_json['response']['docs']
                for doc in docs:
                    yield doc, coll
            except Exception as e:
                logger.error("Failed to parse search results " + str(e))
                continue
        else:
            logger.error("Failed to retrieve doc by id: " + str(
                resp.status_code))
            continue


def find_coinform_claims_by_doc_id(doc_url, cfg):
    assert gcssearch_available
    ci_collections = cfg.get(
        'relsents_in_colls',
        ['fromClaimReviews', 'fromPrecrawled'])
    for doc, coll in gcssearch.find_preindexed_docs_by_url(doc_url,
                                                          ci_collections):
        for claim in doc['claims_content']:
            yield claim, coll


def find_coinform_claims_in_doc(doc_url, unresolved_url, tweetID, cfg):
    for claim_content, coll in find_coinform_claims_by_doc_id(doc_url, cfg):
        sent = claim_content['content'].encode("ascii",
                                               errors="ignore").decode()
        sent = sent.replace("\n", "").replace("\t", "").replace("\r", "")
        yield {
            '@type': 'Sentence',
            'text': sent,
            'in_doc': doc_url,
            'url_in_tweet': unresolved_url,
            'extractor': 'Co-inform content collector, collection '+coll,
        }


def do_analyze_doc(scraped_page, cfg):
    sa_cfg = {**cfg,
              'expand_claims': True}
    return semalizer.analyze_doc(scraped_page, sa_cfg)


def gen_claims_from_analysed_doc(doc, cfg):
    def cleanup_content(content):
        "Needed for content returned by Solr?"
        result = content.encode("ascii", errors="ignore").decode()
        result = result.replace("\n", "").replace("\t", "").replace("\r", "")
        return result

    claim_contents = doc.get('claims_content', [])
    sent_output_list = [cleanup_content(cc['content'])
                        for cc in claim_contents]
    for sent in sent_output_list:
        yield {
            '@type': 'Sentence',
            'text': sent,
            'in_doc': doc.get('resolved_url',
                              doc.get('url',
                                      doc.get('id'))),
            'extractor': doc.get('extractor', 'unknown')
        }


def claims_by_ciapi_from_html(scraped_page, unresolved_url, tweetID, cfg):
    try:
        doc = {**scraped_page,
               'url': unresolved_url}
        sa_cfg = {**cfg,
                  'expand_claims': True}
        analyzed = semalizer.analyze_doc(doc, sa_cfg)
        claim_contents = analyzed.get('claim_content', [])
        sent_output_list = [cc['content'] for cc in claim_contents]
        for sent in sent_output_list:
            sent = sent.replace("\n", "").replace("\t", "").replace("\r", "")
            yield {
                '@type': 'Sentence',
                'text': sent,
                'in_doc': scraped_page['resolved_url'],
                'url_in_tweet': unresolved_url,
                'extractor': '%s-CIAPI' % scraped_page['extractor'],
                'linked_by_tweet': tweetID
            }
    except Exception as e:
        logger.error(e, exc_info=True)


def analyzed_doc(url, cfg):
    logger.info("Scraping " + url)
    start = citimings.start()
    scraped = url_scraper.scrape(url)
    scraped_t = citimings.timing('url_scraping', start)

    resolved_url = scraped['resolved_url']
    # resp2 = requests.get(url)
    # resolved_url = resp2.url
    # logger.info("Resolved to " + resolved_url)
    # url_html = resp2.text
    start2 = citimings.start()
    ci_collections = cfg.get(
        'relsents_in_colls',
        ['pilot-se', 'pilot-gr', 'pilot-at', 'factcheckers', 'fc-dev'])
    assert cisearch_available
    preidx_doc = cisearch.find_preindexed_doc_by_url(resolved_url, ci_collections)
    preidx_doc_t = citimings.timing('retrieve_preindexed', start2)
    if preidx_doc is not None:
        logger.info(
            'Found previously analyzed doc with %s claims and keys %s' % (
                len(preidx_doc.get('claims_content', [])),
                list(preidx_doc.keys())
            ))
        preidx_doc['timings'] = citimings.timing(
            'analyzed_doc', start, [scraped_t, preidx_doc_t])
        return preidx_doc
    logger.info('Document not in existing indices, analysing...')
    start3 = citimings.start()
    result = do_analyze_doc(scraped, cfg)
    do_analyze_t = citimings.timing('semantic_analysis', start3)
    result['timings'] = citimings.timing(
        'analyzed_doc', start, [scraped_t, preidx_doc_t, do_analyze_t])
    return result


def build_in_linked_info(tweetID, urls, cfg):
    # TODO: refactor
    # why extract claims here? let predictor assess credibility of doc
    # so no need to extract sentences here
    in_linked_doc = []
    for url in urls:
        start = citimings.start()
        try:
            adoc = analyzed_doc(url, cfg)
            adoc_t = adoc['timings']
            claims_in_doc = list(gen_claims_from_analysed_doc(adoc, cfg))
            logger.info('Extracted %d claims from url' % len(claims_in_doc))
            claims_in_doc = [
                {**claim,
                 'url_in_tweet': url,
                 'timings': citimings.timing(
                     'url_in_tweet_claim_extraction', start, [adoc_t]),
                 'linked_by_tweet': tweetID}
                for claim in claims_in_doc]
            in_linked_doc.extend(claims_in_doc)
        except Exception as e:
            print("Unresolved url: ", url, "\n", str(e))
            raise e
    return in_linked_doc


def extract(tweetID, tweet, cfg, sentence_detector):
    how = cfg.get("sentence_extractor", 'nltk')
    sentence_type = cfg.get('sentence_type', 'full_sentence')

    urls = find_url(tweet)
    for url in urls:
        tweet = tweet.replace(url, " ")
    tweet = tweet.replace("\n", " ")

    urls = [url.strip() for url in urls]

    sent_list = sentence_detector(tweet)

    json_res = {
        'in_tweet': build_in_tweet_info(tweetID, sent_list, cfg),
        'in_linked_doc': build_in_linked_info(tweetID, urls, cfg)
    }
    path = 'tweet-%s-%s-%s.json' % (tweetID, how, sentence_type)
    with open(path, 'w', errors='replace') as outfile:
        json.dump(json_res, outfile, indent=4)


def open_cogito_disambiguator(sensei_dir):
    from senseiutils import disambiguator
    if hasattr(disambiguator.sensei, 'handle') and disambiguator.sensei.handle > 0:
        return disambiguator
    disambiguator.open(sensei_dir)
    msg = "Failed to open disambiguator."
    msg += " Check path %s and check disambiguator .so or .dll." % sensei_dir
    assert hasattr(disambiguator.sensei, 'handle'), msg
    assert disambiguator.sensei.handle is not None, msg
    assert disambiguator.sensei.handle > 0, msg
    return disambiguator


def cogito_sent_detector_fn(disambiguator):
    def sent_detect(text):
        dis_data = disambiguator.disambiguate(text)
        sent_list = []
        for s in dis_data['sentences']:
            sentence = []
            for g in s["g"]:
                group = dis_data['groups'][g]
                if("t" in group):
                    for t in group['t']:
                        token = dis_data['tokens'][t]
                        if("it" in token):
                            sentence.append(token["fit"])
            sent_list.append(" ".join(sentence))
        return sent_list
    return sent_detect


def build_sent_detector(cfg):
    how = cfg.get('sentence_extractor', 'nltk')
    if how == 'sensei':
        sensi_dir = cfg.get('sensi_dir')
        disamb = open_cogito_disambiguator(sensi_dir) # '/data/sensigrafo/en-14.2/'
        return cogito_sent_detector_fn(disamb)
    elif how == 'nltk':
        import nltk.data
        import nltk
        try:
            nltk.download('punkt')
        except Exception as e:
            logger.error(e)
        tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
        def nltk_sent_detector_fn(text):
            try:
                return tokenizer.tokenize(text)
            except Exception as e:
                logger.error('', e)
                return []
                                        
        return nltk_sent_detector_fn
    else:
        raise ValueError("Unsupported sentence extractor method " + how)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Extract tweet info',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-tweet', help='Tweet to analyze', required=True)
    parser.add_argument('-tweetID', help='Tweet ID to analyze', required=True)
    parser.add_argument('-how', default='sensei', choices=['sensei', 'nltk'],
                        help='Strategy name for extracting sentences',
                        required=False)
    parser.add_argument('-sentence_type', default='full_sentence',
                        choices=['full_sentence', 'clause'],
                        help='Type of sentence', required=False)
    parser.add_argument(
        '-sensi_dir',
        help='Path to sensigrafo folder. Required when using sensei')

    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)
    lformat = logging.Formatter(
        '%(asctime)s %(name)s:%(levelname)s: %(message)s')
    lsh = logging.StreamHandler(sys.stdout)
    lsh.setFormatter(lformat)
    root_logger.addHandler(lsh)

    args = parser.parse_args()

    config = {
        'sentence_extractor': args.how,
        'sentence_type': args.sentence_type,
        'sensi_dir': args.sensi_dir,
        'ciapi_gsl_id': 10021140,
        'ciapi_gsl_dispatcher_host': '192.168.192.163',
        'ciapi_gsl_dispatcher_port': 5400,
        'ciapi_gsl_perm_conn': False,
        'ciapi_sa_base_url': 'https://192.168.192.163:9322',
        'relsents_in_colls': ['pilot-se', 'pilot-gr', 'pilot-at',
                              'factcheckers', 'fc-dev'],
        'relsents_search_auth_user': 'testuser',
        'relsents_search_auth_pwrd': 'testpass',
        'relsents_search_url': 'http://localhost:8070/test/api/v1/search',
        'relsents_search_verify': False
    }
    extract(args.tweetID, args.tweet, config,
            build_sent_detector(config))
