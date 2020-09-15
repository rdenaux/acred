# This file is used to load all the resources required by this module
# ideally this should be done only once
from claimneuralindex import config, claim_neural_index
from stance import stancepred, fnc1
import logging


logger = logging.getLogger(__name__)

## First load the indexed vector space needed for finding semantically
## similar sentences
# e.g. 'http://localhost:8070/'
sem_encoder_url = config['claimneuralindex']['semencoder_url']
claim_embeddings = config['claimneuralindex']['claim_embeddings_path']

# searchable vec space: a dict that can be used by
#  claim_neural_index.search_vector_space
vec_space = {
    **claim_neural_index.load_tsv_vector_space(claim_embeddings),
    **claim_neural_index.vec_space_encoder_from_web_service_url(
        sem_encoder_url)
}


## Next, load the stance detector. For now this also provided by the
##  claimneuralindex. In the future we may consider moving it to its own
##  project/docker container
# e.g. 'C:/models/coinform/saved_fnc1_classifier_acc_0.92'
saved_fnc1_model_path = config['stance']['fnc1_model_path']
logger.info('Loading saved stance detection model from %s' % (
    saved_fnc1_model_path))
stance_tokmodmeta = stancepred.load_saved_fnc1_model(saved_fnc1_model_path)
logger.info('Stance detection model loaded %s' % (
    stance_tokmodmeta['model_meta']))
fnc1.test_model(stance_tokmodmeta, config['stance'])
