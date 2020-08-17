#
# Copyright (c) 2020 Expert System Iberia
#
"""Provides methods to process content types relevant to `acred`

This may involve identifying dicts as specific types of content,
converting between content types. Generating unique identifiers for
content.
"""
from urllib.parse import urlparse
import logging
from esiutils import dictu, hashu


logger = logging.getLogger(__name__)

ci_context = "http://coinform.eu"

# maps Co-inform types to metadata useful for analysing 
_acred_schema = {}


def register_acred_type(type_name, schema_dict):
    """Registers a new acred schema type

    :param type_name: str for the type to register
    :param schema_dict: a dict with schema fields, this must include keys 
      `super_types` a list of type names which are super types
      `ident_keys` for the keys which uniquely identify items for the type_name
      `route_template` a template for the calculated url route and 
      `itemref_keys` for the keys which refer to other items
    :returns: True if the type was registered. If the type_name was
      already registered, an exception will be raised
    :rtype: bool
    """
    if type_name in _acred_schema:
        raise ValueError('A schema for %s was already registered. %s' % (
            type_name, 'Duplicates are not allowed'))
    # validate schema_dict
    assert 'ident_keys' in schema_dict
    assert 'itemref_keys' in schema_dict
    _acred_schema[type_name] = schema_dict
    return True


register_acred_type('Rating', {
    'super_types': [],
    'ident_keys': ['@type', 'reviewAspect', 'ratingValue', 'confidence', 'ratingExplanation'],
    'route_template': '/rating/{identifier}',
    'itemref_keys': []
})

register_acred_type('AggregateRating', {
    'super_types': ['Rating'],
    'ident_keys': ['@type', 'reviewAspect', 'ratingValue', 'confidence', 'ratingExplanation',
                   'ratingCount', 'reviewCount'],
    'route_template': '/rating/{identifier}',
    'itemref_keys': []
})

register_acred_type('WebPage', {
    'super_types': ['CreativeWork'],
    'ident_keys': ['@type', 'url'],
    # 'route_template': None, # already has a url, so no local route needed
    'itemref_keys': ['mentioned_in']
})

register_acred_type('Article', {
    'super_types': ['CreativeWork'],
    'ident_keys': ['@type', 'url'],
    # 'route_template': None, # already has a url, so no local route needed?
    'itemref_keys': []
})


register_acred_type('Sentence', {
    'super_types': ['CreativeWork'],
    'ident_keys': ['@type', 'text'],
    'route_template': '/sentence/{identifier}',
    'itemref_keys': ['appearance']
})

register_acred_type('Claim', {
    'super_types': ['CreativeWork', 'Sentence'],
    'ident_keys': ['@type', 'text'],
    'route_template': '/sentence/{identifier}',
    'itemref_keys': ['appearance']
})

register_acred_type('Organization', {
    'super_types': [],
    'ident_keys': ['@type', 'name', 'url'],
    'route_template': '/organization/{identifier}', # in case no URL is available
    'itemref_keys': []
})

register_acred_type('Person', {
    'super_types': [],
    'ident_keys': ['@type', 'name', 'url'],
    'route_template': '/person/{identifier}', # in case no URL is available
    'itemref_keys': []
})

register_acred_type('schema:Organization', {
    'super_types': [],
    'ident_keys': ['@type', 'name', 'url'],
    'route_template': '/organization/{identifier}',
    'itemref_keys': []
})

# FIXME: copied from claimencoder/claim_encoder.py
#  ideally, it should already come with an identifier, so we don't need to
#  know about this here
register_acred_type('SentenceEncoder', {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion',
                   'author', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['author']   
})

# FIXME: copied from claimneuralindex/claim_neural_index.py
# 
register_acred_type('SemSentSimReviewer', {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion',
                   'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['author']   
})

def super_types(item_or_typename):
    """Returns a list of super type names for an item or typename

    :param item_or_typename: either an item (dict with `@type` field)
      or a typename (str)
    :returns: a list of type names
    :rtype: list
    """
    if is_item(item_or_typename):
        return super_types(item_or_typename['@type'])
    typename = item_or_typename
    assert type(typename) is str, 'Not a type name: %s %s' % (type(typename), typename)
    if typename in _acred_schema:
        return dictu.get_in(_acred_schema, [typename, 'super_types'])
    else:
        logger.warning('Type name %s has not been registered' % typename)
        return []
                    

def ident_keys(item_or_typename):
    """Returns a list of ident keys for item or typename

    :param item_or_typename: either an item (dict with `@type` field)
      or a typename (str)
    :returns: a list of keys whose values uniquely identify the given
      item or typename
    :rtype: list
    """
    if is_item(item_or_typename):
        return ident_keys(item_or_typename['@type'])
    typename = item_or_typename
    assert type(typename) is str, 'Not a type name: %s %s' % (type(typename), typename)
    if typename in _acred_schema:
        return dictu.get_in(_acred_schema, [typename, 'ident_keys'])
    else:
        raise ValueError('Type name %s has not been registered' % typename)

def route_template(item_or_typename):
    """Returns the route template for the item

    :param item_or_typename: either an item (dict with `@type` field)
      or a typename (str)
    :returns: a "new style" python string template
    :rtype: str
    """
    if is_item(item_or_typename):
        return route_template(item_or_typename['@type'])
    typename = item_or_typename
    assert type(typename) is str, 'Not a type name: %s %s' % (type(typename), typename)
    if typename in _acred_schema:
        return dictu.get_in(_acred_schema, [typename, 'route_template'])
    else:
        raise ValueError('Type name %s has not been registered' % typename)
    
    
def itemref_keys(item_or_typename):
    """Returns a list of itemRef keys for item or typename

    An itemRef key is a key whose value is another (single or a list
    of) item. Therefore, the values can be represented either as
    expanded items, but also as references to those items, typically a
    string with the identifier (but also possibly a url).

    :param item_or_typename: either an item (dict with `@type` field)
      or a typename (str)
    :returns: a list of keys for the type which refer to other items
    :rtype: list
    """
    if is_item(item_or_typename):
        return itemref_keys(item_or_typename['@type'])
    typename = item_or_typename
    assert type(typename) is str, 'Not a type name: %s %s' % (type(typename), typename)
    if typename in _acred_schema:
        return dictu.get_in(_acred_schema, [typename, 'itemref_keys'])
    else:
        raise ValueError('Type name %s has not been registered' % typename)
    
###
## Identify doc types
###

def is_dict(d):
    return type(d) == dict

def is_item(d):
    return is_dict(d) and '@type' in d

def is_tweet_doc(doc):
    return doc['@type'] in ['Tweet', 'SocialMediaPosting']


def is_article_doc(doc):
    return doc['@type'] in ['Article', 'Webpage']


def is_creativework(d):
    return is_item(d) and d['@type'] in ['CreativeWork', 'Article', 'Webpage', 'Tweet', 'SocialMediaPosting']


def is_sentence(doc):
    return is_item(doc) and doc['@type'] in ['Sentence', 'Claim']

def is_sentence_pair(doc):
    return is_item(doc) and doc['@type'] in ['SentencePair']

def is_website(d):
    return is_item(d) and d['@type'] in ['WebSite']

def is_webSite(d):
    return is_website(d)

def is_rating(d):
    return is_item(d) and d['@type'] in ['Rating', 'AggregateRating', 'schema:Rating']

def is_review(d):
    return is_item(d) and ('Review' in [d['@type']] + d['additionalType'])

def is_claimReview(d):
    return is_item(d) and d['@type'] in ['ClaimReview', 'schema:ClaimReview']

def is_SimilarSent(d):
    return is_item(d) and d['@type'] in ['SimilarSent']

def is_WebSiteCredReview(d):
    return is_item(d) and d['@type'] in ['WebSiteCredReview']


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


def item_matches_type(d, qtypes):
    assert is_item(d), '%s' % (d)
    assert type(qtypes) is list
    assert len(qtypes) > 0
    dtypes = d.get('additionalType', []) + [d.get('@type', 'Thing')]
    matches = set(dtypes) & set(qtypes)
    return len(matches) > 0

def empty(s):
    if s is None:
        return True
    return len(s) == 0

###
## Validate doc types
###


def validate_tweet(tweet):
    assert tweet['tweet_id'] is not None
    assert type(tweet['tweet_id']) in [int, str]
    logger.debug("Validating tweet %s " % tweet['tweet_id'])
    int(tweet['tweet_id']) # should be able to convert to int
    return True


def validate_article(doc):
    assert doc['url'] is not None
    return True


def validate_doc(doc):
    assert type(doc) is dict, '%s' % (
        'Doc to acred must be a dict not ' + str(type(doc)))
    assert '@context' in doc, 'Missing @context %s' % (
        list(doc.keys()))
    assert '@type' in doc, 'Missing @type'
    assert doc['@context'] in ['http://schema.org', 'http://coinform.eu']
    if is_tweet_doc(doc):
        return validate_tweet(doc)
    elif is_article_doc(doc):
        return validate_article(doc)
    return False


def validate_docs(docs):
    assert type(docs) == list
    for doc in docs:
        validate_doc(doc)
    return True


###
# Convert between types
###

def as_dbq_sentpair(dbSent, qSent, cfg, dbSent_appearance=[]):
    sentA = as_sentence(qSent, cfg=cfg)
    sentB = as_sentence(dbSent, appearance=dbSent_appearance, cfg=cfg)
    text = ' <sep> '.join(sorted([qSent, dbSent]))
    ident = hashu.calc_str_hash(text)
    return {
        '@context': ci_context,
        '@type': 'SentencePair',
        'identifier': ident,
        'url': '%s/sentencepair?querySentence=%s&sentenceInDB=%s' % (ci_context, qSent, dbSent),
        'additionalTypes': ['ItemPair', 'CreativeWork'],
        'description': 'CreativeWork consisting of exactly two sentences',
        'sentA': sentA,
        'roleA': 'querySentence',
        'sentB': sentB,
        'roleB': 'sentenceInDB',
        'text': text
    }


def as_sentence(s, appearance=[], cfg={}):
    if (is_sentence(s)):  # already a Sentence
        return s
    
    for a in appearance:
        assert is_url(a) or is_creativework(a), 'Expecting URL or CreativeWork not %s' (a)
    assert type(s) == str
    ident = hashu.calc_str_hash(s)
    return {
        '@context': ci_context,
        '@type': 'Sentence',
        'identifier': ident,
        'text': s,
        'additionalTypes': ['CreativeWork'],
        'description': 'A single sentence, possibly appearing in some larger document',
        'appearance': appearance
    }


def str_as_website(s):
    """Converts a string into a Website

    :param s: Either a url or a domain name
    :returns: a `WebSite` dict
    :rtype: dict
    """
    assert type(s) == str, '%s' % (type(s))
    assert len(s) > 0, s
    if is_url(s):
        parsed = urlparse(s)
        url = '%s://%s/' % (parsed.scheme, parsed.netloc)
        domain = domain_from_url(url)
    else:
        domain = s
        url = 'http://%s/' % domain
        assert is_url(url), 'Invalid domain? %s' % (domain)
    return {
        '@type': 'WebSite',
        'url': url,
        'identifier': url,
        'name': domain
    }

def try_fix_url(url):
    """Tries to fix some common broken url values

    E.g. http:/example.com/a/b (incorrect scheme separator)

    :param url: str with a possibly broken url
    :returns: the original url or a fixed version
    :rtype: str
    """
    if is_url(url):
        return url
    parsed = urlparse(url)
    if parsed.scheme and (not parsed.netloc) and parsed.path and parsed.path.startswith('/'):
        # e.g. http:/example.com/a/b  (ie incorrect separator ://)
        return '%s:/%s%s' % (
            parsed.scheme, parsed.path,
            '' if not parsed.query else '?%s' % parsed.query)
    logger.warning('Could not fix url %s' % url)
    return url

def domain_from_url(url):
    """Returns the website part of a given url

    :param url: str the URL for which the website is needed
    :returns: the website extracted from the url value
    :rtype: str (or None)
    """
    if url is None:
        return None
    try:
        parsed = urlparse(url)
        if parsed.netloc == 'web.archive.org':
            # special case: try to extract the retrieved url
            path = parsed.path
            try:
                index = path.find('http')
                real_url = path[index:]
                return domain_from_url(try_fix_url(real_url))
            except:
                pass
        return parsed.netloc
    except Exception as e:
        logger.error("Failed to extract netloc from url")

