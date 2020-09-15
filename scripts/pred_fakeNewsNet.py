#
# 2020 ExpertSystem
#
'''Script for generating acred reviews for the fakeNewsNet dataset

See https://github.com/KaiDMML/FakeNewsNet for instructions on how to
retrieve the texts from the article URLs

See also scripts/fetch-data.sh, which should download the input json file
and place it in the `data/evaluation/` folder.

'''
import argparse
from urllib.parse import urlparse
import time
import json
import os
import os.path as osp
import requests
import traceback
import pandas as pd
import logging
import sys
import datetime

logger = logging.getLogger(__name__)

def arg_parser():
    parser = argparse.ArgumentParser(
        description='Reviews the credibility of part of the FakeNewsNet dataset',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-fakeNewsNetFolder',
        help='Path to the fakenewsnet_dataset folder',
        required=True)
    parser.add_argument(
        '-data_feature', choices=['news_articles'], default='news_articles',
        help='Currently, only support for "news_articles" (in future we could add support for "tweets")')
    parser.add_argument(
        '-news_source', choices=['politifact', 'gossipcop'], default='politifact',
        help='Either "politifact" or "gossipcop"')
    parser.add_argument(
        '-acredapi_url',
        help='URL of the acredapi base URL',
        required=True)
    parser.add_argument(
        '-config',
        help='Path to a json file with configurations for semantic analysis')
    parser.add_argument(
        '-output_dir', type=str,
        help='Path to a Name of the co-inform collection where to store the analyzed documents')
    return parser

def _setup_logging():
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)
    lformat = logging.Formatter(
        '%(asctime)s %(name)s:%(levelname)s: %(message)s')
    lsh = logging.StreamHandler(sys.stdout)
    lsh.setFormatter(lformat)
    root_logger.addHandler(lsh)


def gen_data_feature_files(based_dirs, data_feature):
    for base_dir in base_dirs:
        for item_dir in os.listdir(base_dir):
            if data_feature == 'news_articles':
                yield item_dir, '%s/%s/news content.json' % (base_dir, item_dir)
            elif data_features == 'tweets':
                tweet_dir = '%s/%s/tweets' % (base_dir, item_dir)
                if not os.path.exists(tweet_dir):
                    continue
                for tweet_json in os.listdir(tweet_dir):
                    yield tweet_json.replace('.json', ''), '%s/%s' % (tweet_dir, tweet_json)
            else:
                raise ValueError('%s' % data_feature)

def guess_parse_datetime(s):
    assert type(s) is str, 'Expecting str but found %s' % type(s)
    supported_formats = [
        '%c', # locale
        '%a %b %d %H:%M:%S %z %Y', # twitter-like
        "%Y-%m-%dT%H:%M:%S%z" # isodate
    ]
    for date_format in supported_formats:
        try:
            dt = datetime.datetime.strptime(s, date_format)
            return dt
        except ValueError as e:
            pass
    raise ValueError('Unable to parse date string %s' % s)

def as_utc_timestamp(dt):
    """Converts a `datetime` object into a UTC timestamp string

    :param dt: a `datetime` as generated by the `datetime` library
    :returns: timestamp with format 'YYYY-MM-ddThh:mm:ss.microsecsZ'
    :rtype: str
    """
    if type(dt) == float:
        # assume timestamp
        # print('converting timestamp', dt, 'onto datetime')
        dt = datetime.datetime.fromtimestamp(dt)
    if type(dt) == datetime.date:
        dt = datetime.datetime.combine(dt, datetime.datetime.min.time())
    assert type(dt) == datetime.datetime, 'Should be datetime, but is %s' % (
        type(dt))
    # print('converting dt', dt, type(dt), 'onto utc iso format')
    utc_dt = dt.replace(tzinfo=datetime.timezone.utc)
    return utc_dt.isoformat().replace('+00:00', 'Z')

def as_iso_date(date_val):
    if date_val is None:
        return None
    if type(date_val) is float:
        return as_utc_timestamp(date_val)
    dt = guess_parse_datetime(date_val)
    if dt is None:
        return None
    return as_utc_timestamp(dt)

def empty(s):
    if s is None:
        return True
    return len(s) == 0

def is_url(s):
    if type(s) != str:
        return False
    try:
        parsed = urlparse(s)
        return not (empty(parsed.scheme)  or
                    empty(parsed.netloc))
    except Exception as e:
        logger.exception(e)
        return False

def fix_url(url):
    if not url.startswith('http'):
        fixed = 'http://%s' % url
        if content.is_url(fixed):
            return fixed
        else:
            raise ValueError("Assumed missing scheme for %s" % url)
    raise ValueError('Do not know how to fix url %s' % url)
    
def fnn_doc_as_article(fnn_news_content):
    url = fnn_news_content['url']
    if not is_url(url):
        try:
            url = fix_url(url)
        except Exception as e:
            pass
    pubDate = fnn_news_content.get('publish_date', None)
    publishedDate = as_iso_date(pubDate)
    return {
        '@context': 'http://schema.org',
        '@type': 'Article',
        'url': url,
        'content': fnn_news_content.get('text', ''),
        'title': fnn_news_content.get('title', ''),
        'publishedDate': publishedDate
    }

def try_write_review_to_outdir(review, doc, args):
    if not args.output_dir:
        return
    out_path = '%s/%s.json' % (args.output_dir, doc['id'])
    try:
        with open(out_path, 'w') as f_out:
            json.dump(review, f_out, indent=2)
    except Exception as e:
        print('Failed to write %s %s' % (out_path, e))

def review_article(ditem, args):
    url = '%s/acred/api/v1/acred/reviewer/credibility/webpage' % args.acredapi_url
    req = {
        'webpages': [ditem]
    }
    resp = requests.post(url, verify=False, json=req)
    resp.raise_for_status()
    respd = resp.json()
    assert type(respd) is list
    assert len(respd) == 1  # single doc requested
    review = respd[0]
    try_write_review_to_outdir(review, ditem, args)
    return review

def acred_rating_as_acred_label(rating):
    score = rating['ratingValue']
    confidence = rating['confidence']
    if confidence < 0.7:
        return 'not verfiable'
    if score > 0.5:
        return 'credible'
    elif score >= 0.25:
        return 'mostly credible'
    elif score >= -0.25:
        return 'credibility uncertain'
    elif score >= -0.5:
        return 'mostly not credible'
    elif score >= -1.0:
        return 'not credible'
    else:
        raise ValueError('Wrong credibility values %s %s' % (score, confidence))
    return label

def acred_rating_as_fakeNewsNet_label(rating):
    acred_label = acred_rating_as_acred_label(rating)
    if acred_label in ['credible', 'mostly credible']:
        return  'real'
    else:
        return 'fake'
        
if __name__ == '__main__':
    parser = arg_parser()
    _setup_logging()
    args = parser.parse_args()

    if args.config is not None:
        with open(args.config, 'r', encoding='utf8') as cfg_file:
            config = {**json.load(cfg_file)}

    assert osp.isdir(osp.join(args.output_dir))
    start = time.time()
    
    base_dirs = ['%s/%s/%s' % (args.fakeNewsNetFolder, args.news_source, news_label)
                 for news_label in ['fake', 'real']]
    print('base_dirs %s' % base_dirs)
    preds = []
    for item_id, json_path in gen_data_feature_files(base_dirs, args.data_feature):
        if not os.path.exists(json_path):
            preds.append({
                'item_id': item_id, 'label': 'not_verifiable',
                'explanation': 'Missing FakeNewsNet input json'})
            continue
        with open(json_path, 'r', encoding='utf-8') as in_file:
            fnn_content = json.load(in_file)
            in_doc = {
                **fnn_doc_as_article(fnn_content),
                'id': item_id
            }
            review = review_article(in_doc, args)
            print('review keys', list(review.keys()))
            preds.append({
                'item_id': item_id,
                'label': acred_rating_as_fakeNewsNet_label(review['reviewRating']),
                'acred_label': acred_rating_as_acred_label(review['reviewRating']),
                'explanation': review['text']
            })
            
    path = '%s/predictions.csv' % (args.output_dir)
    pd.DataFrame(preds).to_csv(path)
    
    end = time.time()
    timing = "%s s" % (end - start)
    print('Processed %s folders from %s. Stored in %s. Timings: %s' % (
        len(preds), base_dirs, args.output_dir, timing))