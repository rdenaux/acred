import logging
from langdetect import detect


logger = logging.getLogger(__name__)


def is_english(content):
  try:
    return detect(content) == 'en'
  except:
    # e.g. because content is empty
    return False


