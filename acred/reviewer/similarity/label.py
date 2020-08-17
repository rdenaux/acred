#
# Copyright (c) 2019 Expert System Iberia
#
"""
Provides functions for generating labels for similarity values
"""

def claim_rel_str(sim_val, sent_stance):
    if sent_stance is None:
        return 'is %s to' % similarity_str(sim_val)
    if sent_stance == 'agree':
        return 'agrees with'
    elif sent_stance == 'disagree':
        return 'disagrees with'
    elif sent_stance == 'unrelated':
        return 'is similar(?) but unrelated to'
    else:  # discuss
        return 'is %s to and discussed by' % similarity_str(sim_val)


def similarity_str(sim_val):
    if sim_val >= 0.9:
        return "very similar"
    if sim_val >= 0.75:
        return "similar"
    if sim_val >= 0.6:
        return "vaguely related"
    return "not so similar"    
