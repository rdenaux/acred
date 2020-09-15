# This file is used to load all the resources required by this module
# ideally this should be done only once
from worthiness import config, worthinesspred, clef19
import logging


logger = logging.getLogger(__name__)

##  Load the worthiness checker
# e.g. 'C:/models/coinform/saved_checkworthiness_classifier_acc_0.95'
check_worthiness_model_path = config['worthinesschecker']['check_worthiness_model_path']
logger.info('Loading saved check-worthiness model from %s' % (
    check_worthiness_model_path))
worthiness_tokmodmeta = worthinesspred.load_saved_cw_model(check_worthiness_model_path)
logger.info('Check_worthiness model loaded %s' % (
    worthiness_tokmodmeta['model_meta']))

clef19.test_model(worthiness_tokmodmeta, config['worthinesschecker'])
