#
# 2020 ExpertSystem
#
'''Script for generating predictions for the coinform250 dataset
 using the acred predictor

See https://github.com/co-inform/Datasets

See also scripts/fetch-data.sh, which should download the input json file
and place it in the `data/evaluation/` folder.
'''
import argparse
import time
import json
import os
import os.path as osp
import requests
import traceback
import pandas as pd


def ensure_req_tweet_content(req):
    for t in req['tweets']:
        c = t['content']
        if c is None:
            t['content'] = ''
            print('Fixed null content')

def acred_as_coinfo_label(credreview, thresh=0.4):
    assert thresh >= 0.0
    assert thresh <= 1.0
    conf = credreview['reviewRating']['confidence']
    if conf <= thresh:
        return  'not_verifiable'
    
    val = credreview['reviewRating']['ratingValue']
    if val >= 0.5:
        return 'credible'
    if val >= 0.25:
        return 'mostly_credible'
    if val >= -0.25:
        return 'credible_uncertain'
    if val >= -0.5:
        return 'mostly_not_credible'
    return 'not_credible'


def exec_req(i, req, args):
    print('\n\nExecuting request %s' % (i))

    ensure_req_tweet_content(req)
    req['reviewFormat'] = 'schema.org'

    start = time.time()
    resp = requests.post(args.credpred_url, json=req,
                         verify=False,
                         timeout=args.req_timeout)
    result = []
    if resp.ok:
        respd = resp.json()
        result = [{
            'tweet_id': request['tweet_id'],
            'ratingValue': r['reviewRating']['ratingValue'],
            'confidence': r['reviewRating']['confidence'],
            'label': acred_as_coinfo_label(r)
        } for request, r in zip(req['tweets'], respd)]
        resp_f = 'coinform250_%s.json' % i
        with open('%s/%s' % (args.outDir, resp_f), 'w') as outf:
            json.dump(respd, outf)
    else:
        print("Failed: %s %s" % (str(resp), resp.text))            

    print('Processed in %ss.' % (time.time() - start))
    return result


def as_acred_requests(tweets, batchSize=1):
    batch = []
    for i, t in enumerate(tweets):
        batch.append({
            'content': t['full_text'],
            'tweet_id': t['id'],
            'url': 'https://twitter.com/x/status/%s' % (t['id'])})
        if len(batch) == batchSize:
            yield {'tweets': batch,
                   'source': 'coinform250.json',
                   'batch_id': '%s-%s' % (i-batchSize, i)}
            batch = []
    if len(batch) > 0:
        yield {'tweets': batch,
               'source': 'coinform250.json',
               'batch_id': '%s-%s' % (len(tweets) - len(batch), len(tweets))}
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate tweet credibility predictions for a dir with requests',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-inputJson',
        help='Path to the coinform250.json file',
        required=True)
    parser.add_argument(
        '-batchSize', type=int, default=1,
        help='Number of tweets to send per request to acred endpoint')
    parser.add_argument(
        '-outDir',
        help='Path to a local dir where the CredibilityReviews will be stored',
        required=True)
    parser.add_argument(
        '-credpred_url',
        help='URL of the acred endpoint for the tweet credibility')
    parser.add_argument(
        '-credpred_id',
        help='ID of the generation task')
    parser.add_argument(
        '-req_timeout',
        type=int, default=90,
        help='Seconds to wait for a response')

    args = parser.parse_args()

    all_start = time.time()

    assert osp.isdir(osp.join(args.outDir))
    assert osp.isfile(args.inputJson)
    tweets = []
    with open(args.inputJson) as jsonl_file:
        tweets = [json.loads(line) for line in jsonl_file]
    assert len(tweets) > 0, '%s' % (len(tweets))
    
    print('Reviewing credibility of %s tweets using batchSize %s' % (len(tweets), args.batchSize))

    preds = []
    for i, req in enumerate(as_acred_requests(tweets, args.batchSize)):
        try:
            preds.extend(exec_req(i, req, args))
        except Exception as e:
            print('Error executing request %s %s %s' % (i, req, str(e)))
            print(traceback.format_exc())

    pd.DataFrame(preds).to_csv('%s/%s.csv' % (args.outDir, 'predictions'), index=False)
    print('Finished in %.3fs' % (time.time() - all_start))
