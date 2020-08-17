#
# Copyright (c) 2019 Expert System Iberia
#
"""
Provides functions for generating labels for credibility reviews
"""


def describe_credval(val, cred_dict):
    """Returns a description of a credibility value, possibly based on a dict

    **deprecated** use rating_label instead, especially when using the
      new schema.org implementation
    
    :param val: float value between -1.0 and 1.0
    :param cred_dict: a credibility dict as returned by misinfome
    :returns: string describing the value
    :rtype: str
    """
    source = None if cred_dict is None else cred_dict.get('source', None)
    if source == 'domain':
        return 'was published in a site (%s) that is %s' % (
            cred_dict.get("domainReviewed", "??"), describe_reliability(val))
    if source == 'claimReview':
        return 'was fact-checked and found to be %s' % describe_accuracy(val)
    if source is None:
        if val >= 0.5:
            return 'credible'
        if val >= 0.25:
            return 'mostly credible'
        if val >= -0.25:
            return 'uncertain'
        if val >= -0.5:
            return 'mostly not credible'
        return 'not credible'
    raise ValueError("Unsupported credibility source " + source)


def rating_label(rating, cfg):
    """Convert a credibility rating into a label

    :param rating: a credibility rating. We assume it has
      `reviewAspect == credibility` and float `confidence` and
      `ratingValue`s
    :param cfg: configuration options
    :returns: a short string to summarise the credibility rating
    :rtype: str
    """
    if 'reviewAspect' in rating:
        assert rating['reviewAspect'] == 'credibility', '%s' % (rating)
    conf_threshold = float(cfg.get('cred_conf_threshold', 0.7))
    if 'confidence' in rating and rating['confidence'] < conf_threshold:
        return 'not verifiable'
    assert 'ratingValue' in rating, '%s' % (rating)
    val = rating['ratingValue']
    assert val <= 1.0 and val >= -1.0, '%s' % (rating)
    if val >= 0.5:
        return 'credible'
    if val >= 0.25:
        return 'mostly credible'
    if val >= -0.25:
        return 'uncertain'
    if val >= -0.5:
        return 'mostly not credible'
    return 'not credible'
    


def describe_reliability(cred_val):
    if cred_val >= 0.5:
        return 'reliable'
    if cred_val >= 0.1:
        return 'mostly reliable'
    if cred_val >= -0.1:
        return 'mixed reliability'
    if cred_val >= -0.5:
        return 'mostly unreliable'
    return 'unreliable'


def describe_accuracy(cred_val):
    if cred_val >= 0.5:
        return 'accurate'
    if cred_val >= 0.1:
        return 'accurate with considerations'
    if cred_val >= -0.1:
        return 'unsubstantiated'
    if cred_val >= -0.5:
        return 'inaccurate with considerations'
    return 'inaccurate'
