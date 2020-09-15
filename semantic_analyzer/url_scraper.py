import sys
import requests
import logging
from bs4 import BeautifulSoup
import argparse
import time
from datetime import datetime
import json
from urllib.parse import urlparse
import functools


""" url_scraper: extracts text and metadata from a given url
"""

logger = logging.getLogger(__name__)


def millis_from(start):
    dt = datetime.now() - start
    secs = (dt.days * 24 * 60 * 60 + dt.seconds)
    ms = secs * 1000 + dt.microseconds / 1000.0
    return ms


@functools.lru_cache(maxsize=128)
def fetch_url(url):
    """Tries to fetch a url

    :param url: possibly unresolved url
    :returns: a dict with keys 'resolved_url' and 'raw_content'
    :rtype: dict
    """
    logger.info("Resolving " + url)
    try:
        resp = requests.get(url, timeout=1.5)
        resp.raise_for_status()
        return {
            "resolved_url": resp.url,
            "raw_content": resp.text
        }
    except Exception as e:
        logger.error('Error fetching %s' % url, e)
        return {
            "resolved_url": url,
            "raw_content": "",
            "url_error": str(e)
        }


def extract_text_from_html(html_str):
    soup = BeautifulSoup(html_str, 'html.parser')
    article_matches = soup.find_all('article')  # , {'role': 'article'}
    logger.info("Found %d article elements" % len(article_matches))
    if len(article_matches) > 0:
        parafs = [t
                  for art in article_matches
                  for t in art.find_all(text=True) if t.parent.name == 'p'
                  ]
        #texts = [art.text for art in article_matches if art.text.parent.name == 'p']
        return " ".join(parafs).encode('utf-8').decode()
    parafs = [t for t in soup.find_all(text=True) if t.parent.name == 'p']
    logger.info("Found %d paragraphs" % len(parafs))
    return " ".join(parafs).encode("utf-8", errors="ignore").decode()


def extract_title(html_str, all_meta):
    soup = BeautifulSoup(html_str, 'html.parser')
    try:
        return soup.title.string
    except Exception as e:
        return None


def fix_md_item(item):
    if type(item) is list:
        if len(item) == 1:
            return fix_md_item(item[0])
        else:
            return [fix_md_item(it for it in item)]
    if type(item) is not dict:
        return item
    typ = item.get('type')
    id = item.get('id')
    props = item.get('properties')
    fixed_props = {propname: fix_md_item(val)
                   for propname, val in props.items()}
    result = {**fixed_props}
    if typ:
        if type(typ) == list and len(typ) > 1:
            logger.warning('selecting one type from', typ)
        typ = typ[0]  # select first if multiple
        lastslash = typ.rfind('/')
        if lastslash > 0:
            result['@context'] = typ[:lastslash]
            result['@type'] = typ[lastslash+1:]
        else:
            result['@type'] = typ
    if id:
        result['id'] = id
    return result


def extract_microdata_from_html(html_str):
    import microdata
    try:
        items = microdata.get_items(html_str)
        return [item.json_dict() for item in items]
    except Exception as e:
        return [{'extraction_error': str(e)}]


def try_parse_json(s):
    try:
        return json.loads(s)
    except Exception as e:
        logger.error('Failed to parse json ' + str(e), e)
        return {}


def extract_jsonld_from_html(html_str):
    soup = BeautifulSoup(html_str, 'html.parser')
    jlds = soup.find_all('script', {'type': 'application/ld+json'})
    contents = [jld.text for jld in jlds]
    return [try_parse_json(c) for c in contents]


def extract_meta_tags(html_str):
    prop_prefixes = ['article:', 'og:', 'twitter:', 'fb:']
    soup = BeautifulSoup(html_str, 'html.parser')
    result = {}
    filtered_props = []
    for meta in soup.find_all('meta'):
        prop = meta.get('property')
        if prop is None:
            prop = meta.get('name')
        if prop is None:
            continue
        if len([prop
                for prefix in prop_prefixes
                if prop.startswith(prefix)]) == 0:
            filtered_props.append(prop)
            continue
        val = meta.get('content')
        if val:
            result[prop] = val
    if len(filtered_props) > 0:
        logger.debug('Filtered props %s ' % sorted(filtered_props))
    return result


def extract_metadata_from_html(html_str):
    all_meta = {
        'meta_tags': extract_meta_tags(html_str),
        'microdata': extract_microdata_from_html(html_str),
        'json-ld': extract_jsonld_from_html(html_str)
    }
    title = extract_title(html_str, all_meta)
    if title is None:
        title = ''    
    return {
        'title': title,
        'raw_contentLength': len(html_str),
        'contentType': 'text/html',
        **all_meta
    }


def find_pubDate(all_meta):
    try:
        meta_tags = all_meta.get('meta_tags', {})
        if 'article:published_time' in meta_tags:
            return meta_tags['article:published_time']
        jlds = all_meta.get('json-ld', [])
        flat_jlds = []
        for jld in jlds:
            if type(jld) == list:
                flat_jlds.extend(jld)
            elif type(jld) == dict:
                flat_jlds.append(jld)
            else:
                logger.warning('Unexpected jld value %s' % (type(jld)))
        jlds = flat_jlds
        article_types = ['NewsArticle', 'ReportageNewsArticle', 'Article']
        articles = [jld for jld in jlds
                    if jld.get('@type') in article_types]
        pubDates = [art.get('datePublished', None)
                    for art in articles
                    if art.get('datePublished', None) is not None]
        if len(pubDates) > 0:
            return pubDates[0]
    except Exception as e:
        logger.error(e)
    return None


def extract_top_level_meta(all_meta):
    result = {}
    result['title'] = all_meta.get('title', '')
    result['contentLength'] = all_meta.get('raw_contentLength')
    result['publishedDate'] = find_pubDate(all_meta)
    # TODO: author
    # TODO: publisher
    # TODO: domain?
    # TODO: structured_data
    # ??
    return result


def url_domain(url):
    if url is None:
        return None
    try:
        return urlparse(url).netloc
    except Exception as e:
        logger.error("Failed to extract netloc from url")


def scrape(url, include_raw_content=False):
    logger.info("fetching " + url)
    start = datetime.now()
    fetched = fetch_url(url)
    logger.info("Resolved to " + fetched['resolved_url'])
    raw_content = fetched['raw_content']
    # logger.info("raw_content " + fetched['raw_content'])
    content = extract_text_from_html(raw_content)
    metadata = extract_metadata_from_html(raw_content)
    result = {
        **fetched,
        **extract_top_level_meta(metadata),
        'timings': {
            'phase': 'url_scraping',
            'total': millis_from(start)
        },
        'content': content,
        'metadata': metadata,
        'extractor': 'BeautifulSoup-esilab',
        'source': 'BeautifulSoup-esilab',
        'source_id': [url_domain(fetched['resolved_url'])],
        # date?
    }
    if not include_raw_content:
        result.pop('raw_content')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Scrape Text and Metadata for a url',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-url', help='URL to scrape', required=True)
    parser.add_argument(
        '-keep_raw_content',
        type=bool,
        help='Print the raw content, besides the extracted text and metadata',
        default=False)

    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)
    lformat = logging.Formatter(
        '%(asctime)s %(name)s:%(levelname)s: %(message)s')
    lsh = logging.StreamHandler(sys.stdout)
    lsh.setFormatter(lformat)
    root_logger.addHandler(lsh)

    args = parser.parse_args()
    url = args.url
    logging.info("Scraping %s" % url)
    start = time.time()
    result = scrape(url)
    elapsed = (time.time() - start)
    logging.info("Scraped %s in %dms.\n\tresult: %s" % (
        url, elapsed, result))
