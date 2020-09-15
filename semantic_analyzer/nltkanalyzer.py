#
# Copyright (c) 2020 Expert System Iberia
#
"""Provides methods to perform semantic analysis of documents
"""
import nltk.data
import nltk
import logging

logger = logging.getLogger(__name__)

try:
    nltk.download('punkt')
except Exception as e:
    logger.error(e)

tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

def nltk_sent_detector_fn(title, content):
    try:
        return tokenizer.tokenize('%s. %s' % (title, content))
    except Exception as e:
        logger.error('', e)
        return [title]

    
def get_semantic_analysis(content, title, cfg):
    """Perform semantic analysis on a document based on its content and title

    :param content: textual content of the document
    :param title: title of the document
    :param cfg: additional config options
    :returns: a semantic analysis dict
    :rtype: dict
    """
    return {
        # list of claims detected in the title and content
        'claims_content': nltk_sent_detector_fn(title, content) 
    }
    
