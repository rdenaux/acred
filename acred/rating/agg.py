#
# Copyright (c) 2020 Expert System Iberia
#
"""Utilities to aggregate ratings
"""
from acred import content
from esiutils import dictu


def select_most_confident_rating(ratings):
    if len(ratings) == 0:
        return None
    sorted_creds = sorted(ratings,
                          key=lambda cred: cred.get('confidence', -1.0),
                          reverse=True)
    if len(sorted_creds) > 0:
        return sorted_creds[0]  # most confident
    else:
        return None

def select_most_confident_review(reviews, cfg):
    if len(reviews) == 0:
        return None
    
    for rev in reviews:
        assert content.is_review(rev), rev
        
    sorted_revs = sorted(
        reviews,
        # Note: we can sort by multiple values by returning a tuple
        #  with confidence first it may be a good idea to do this to
        #  make this less random if ther are multiple maxima
        key=lambda rev: dictu.get_in(rev, ['reviewRating', 'confidence'], -1.0),
        reverse=True)
    if len(sorted_revs) > 0:
        return sorted_revs[0]  # most confident
    else:
        return None

def filter_review_by_min_confidence(threshold):
    assert type(threshold) == float, 'Should be float not %s' % (type(threshold))
    def filter_fn(review):
        return dictu.get_in(review, ['reviewRating', 'confidence'], 0.0) >= threshold
    return filter_fn

    
def total_reviewCount(ratings):
    for r in ratings:
        assert content.is_rating(r), '%s is not a rating dict' % (r)
    revCounts = [r.get('reviewCount', 0)
                 for r in ratings]
    return sum(revCounts)

def total_ratingCount(ratings):
    for r in ratings:
        assert content.is_rating(r), '%s is not a rating dict' % (r)
    ratCounts = [
        r.get('ratingCount', 0) + 1  # subratings + the rating itself
        for r in ratings]
    return sum(ratCounts)

