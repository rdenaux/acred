#
# Copyright (c) 2019 Expert System Iberia
#
"""Implements creating an indexed vector space

It does this using a path to a folder as well as providing methods for
using such a vecspace to find similar points
"""
import numpy as np
import os
import sys
import logging
import time
import requests
import math
from esiutils import bot_describer, dictu, isodate, hashu


logger = logging.getLogger(__name__)


try:
    import faiss
except ImportError:
    logger.warn('Failed to import faiss. Assuming windows?')


def calc_sim_reviewer_id(sim_reviewer):
    """Calculates a unique id code for a sim_reviewer
    
    :param sim_reviewer a `SemSentSimReviewer` dict
    :returns: a hashcode that tries to capture the identit of the sim_reviewer
    :rtype: str
    """
    return hashu.hash_dict(dictu.select_keys(
        sim_reviewer,
        ['@type', 'name', 'dateCreated', 'softwareVersion',
         'isBasedOn', 'launchConfiguration']))


def sim_reviewer(vec_space, index_format):
    semenc_info = vec_space['semantic_encoder_info_fn']()
    result =  {
        '@context': 'http://coinform.eu',
        '@type': 'SemSentSimReviewer',
        'additionalType': ['SoftwareApplication', 'Bot'],
        'name': 'ESI Sentence Similarity Reviewer %s' % index_format,
        'description': 'Claim neural index that uses a semantic similarity measure based on a semantic encoder. It achieved 83% accuracy on STS-B.',
        'author': bot_describer.esiLab_organization(),
        'dateCreated': '2020-03-19T15:09:00Z',
        'applicationCategory': [ 'NLP' ],
        'applicationSubCategory': ['SemanticSimilarity'],
        'applicationSuite': ['Co-inform'],
        'softwareRequirements': ['python', 'numpy'],
        'softwareVersion': '0.1.0-%s' % index_format,
        'executionEnvironment': bot_describer.inspect_execution_env(),
        'isBasedOn': [semenc_info],
        'launchConfiguration': {
            'vecSpace': vec_space['dataset_info']
        }
    }
    result['identifier'] = calc_sim_reviewer_id(result)
    return result


def normalize(vectors, norm='l2'):
    if len(vectors.shape) == 2:
        axis = 1
    elif len(vectors.shape) == 1:
        axis = 0
    else:
        raise ValueError(
            "Expecting single vector or a matrix of vectors, but found %s" %
            str(vectors.shape))
    norms = np.linalg.norm(vectors, axis=axis)
    return (vectors.T / norms).T


def search_vector_space(vec_space, query_vec, topn=10, index_format=None):
    if type(query_vec) == list:
        qvec = np.array(query_vec, dtype=np.float32)
    elif type(query_vec) == np.ndarray:
        qvec = query_vec.astype('float32')
    else:
        raise ValueError("Expecting list or np array but was %s " % (
            type(query_vec)))

    if len(qvec.shape) == 1:  # single vector
        qvec = np.expand_dims(qvec, axis=0)
    assert len(qvec.shape) == 2, "%s" % str(qvec.shape)
    assert qvec.shape[1] == vec_space['dim'], "%s != %s" % (
        qvec.shape[1], vec_space['dim'])

    logger.info('index_format = %s' % index_format)
    if index_format is None or index_format == 'numpy':
        topn_sims, topn_labels = search_topn_numpy_index(vec_space, qvec, topn)
    elif index_format == 'faiss':
        topn_sims, topn_labels = search_topn_faiss_index(vec_space, qvec, topn)

    return topn_sims, topn_labels


def calc_IVF_nlists_from_N(n):
    """Get an appropriate value for nlists for a given n
    see https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index#if-below-1m-vectors-ivfx

    :param n: number of vectors to index
    :returns: a value between 4*sqrt(N) and 16*sqrt(N) 
      as suggested in the faiss documentation
    :rtype: int
    """
    return int(8*math.sqrt(n))
    

def create_faiss_index(vectors, ndims):
    """
    Create an index based on the faiss library.

    :param vectors: matrix of word embeddings
    :type vectors: numpy array
    :param ndims: number of word embedding dimensions
    :type ndims: int
    :return: vec_index
    :rtype: faiss index object
    """
    if 'faiss' not in sys.modules:
        return None
    assert len(vectors.shape) == 2, '%s' % (vectors.shape)
    nlists = calc_IVF_nlists_from_N(vectors.shape[0])
    nprobe = max(1, int(nlists/100))
    quantizer = faiss.IndexFlatIP(ndims)
    vec_index = faiss.IndexIVFFlat(
        quantizer, ndims, nlists, faiss.METRIC_INNER_PRODUCT)
    assert not vec_index.is_trained
    vec_index.train(vectors)
    assert vec_index.is_trained
    logger.info('Faiss index is trained : %s' % vec_index.is_trained)
    vec_index.add(vectors)  # add vectors to the index
    logger.info('Faiss index n-total : %s' % vec_index.ntotal)
    vec_index.nprobe = nprobe
    logger.info('Faiss index IVFlat with nlists=%d and nprobe=%s' % (
        nlists, vec_index.nprobe))
    logger.warning('Faiss index IVFlat with nlists=%d and nprobe=%s' % (
        nlists, vec_index.nprobe))    
    return vec_index


def search_topn_faiss_index(vec_space, qvec, topn):
    """
    For input query vectors return similar sentences in the faiss index

    :param vec_space: dictionary that contain a field with the faiss index
    :type vec_space: dict
    :param qvec: matrix of query embeddings
    :type qvec: numpy array
    :param topn: number of similar candidates for each query
    :type topn: int
    :return: set of similar vectors found `topn_sims` and their labels
      `topn_labels`
    :rtype: lists
    """
    # logger.info("Calculate vector similarities")
    logger.debug("Calculate vector similarities")
    faiss_indx = vec_space.get('faiss_index', None)
    if faiss_indx is None:
        raise Exception('Faiss index is not available, use numpy instead')
    logger.debug('total faiss index: %s' % faiss_indx.ntotal)
    start = time.time()
    sims, indx = faiss_indx.search(normalize(qvec), topn)
    end = time.time()
    logger.debug("faiss index search time: %ss" % (end - start))
    # logger.debug("Take top similarity scores and labels")
    topn_sims = sims
    topn_labels = np.take(np.array(vec_space['labels']), indx)
    return topn_sims, topn_labels


def search_topn_numpy_index(vec_space, qvec, topn):
    """
    For input query vectors return similar sentences from numpy index

    :param vec_space: dictionary that contain a field with the embeddings
    :type vec_space: dict
    :param qvec: matrix of query embeddings
    :type qvec: numpy array
    :param topn: number of similar candidates for each query
    :type topn: int
    :return: set of similar vectors found `topn_sims` and their labels
      `topn_labels`
    :rtype: lists
    """
    vectors = vec_space['vectors']
    labels = vec_space['labels']
    sims = np.tensordot(normalize(qvec), vectors.T, axes=1)
    # sims shape: (num_qvecs, num_vecs)
    sim_argsort = np.ma.argsort(sims, axis=1)
    top_ids_rev = sim_argsort[:, -topn:]
    # top scores at end, so select and flip
    top_ids = np.flip(top_ids_rev, axis=1)
    topn_sims = np.take_along_axis(sims, top_ids, axis=1)
    topn_labels = np.take(np.array(labels), top_ids)
    return topn_sims, topn_labels


def search_semantic_vecspace(vec_space, qsentences,
                             topn=10, index_format=None):
    """Search the `vec_space` for embeddings semantically similar to `qsentences`
    semantic similarity is performed by the `semantic_encoder`.

    :param vec_space a vector space dict as returned by `load_tsv_vector_space`
    :param qsentences: a list of sentences to query sentences (str)
    :param topn: the number of similar sentences in the vector space to
      return for each query sentence
    :param index_format: index to use possible values `numpy` and `faiss`
    :returns: a list of size `len(qsentences)` which lists (of size `topn`) of
    tuples from claim ids to predicted similarity scores (in range [0.0 1.0])
    :rtype: triple
    """
    logger.info("Encoding %d sentences" % len(qsentences))
    q_vecs = vec_space['sentence_encoder_fn'](qsentences)
    logger.info("Converting list to numpy")
    q_vecs = np.array(q_vecs)  # shape (num_sents, emb_dim)
    logger.info("Search vector space for nearest neighbors")
    q_cosims, q_labels = search_vector_space(
        vec_space, q_vecs, topn=topn, index_format=index_format)
    logger.info("Cosine similarities:" + str(q_cosims))
    logger.info("Most similar labels:" + str(q_labels))
    q_preds = vec_space['cosim2preds_fn'](q_cosims.tolist())
    logger.info("Similarity Preds:" + str(q_preds))
    return q_preds, q_labels.tolist(), sim_reviewer(vec_space, index_format)


def semantic_sent_encoder(sem_encoder_url):
    def encoder_fn(sentences):
        url = sem_encoder_url + '/encode_sents'
        req = {'sentences': sentences}
        resp = requests.post(url, json=req, verify=False)
        logger.info("Response from %s %s" % (url, resp))
        return resp.json()['semantic_encodings']
    return encoder_fn


def semantic_cosim2preds(sem_encoder_url):
    def cosim2pred_fn(cosims):
        url = sem_encoder_url + '/cosim_to_pred_score'
        req = {'cosims': cosims}
        resp = requests.post(url, json=req)
        logger.info("Response from %s %s" % (url, resp))
        return resp.json()['similarity_scores']
    return cosim2pred_fn


def semantic_sent_encoder_info(semencoder_url):
    def fn():
        url = semencoder_url + '/encoder_info'
        resp = requests.get(url, verify=False)
        logger.info("Response from %s %s" % (url, resp))
        return resp.json()['semanticEncoder']
    return fn

def vec_space_encoder_from_web_service_url(semencoder_url):
    """Creates a valid vecspace encoder dict required for searching
    a vector space.

    :param semencoder_url: a URL that implements the semantic encoder
      API. i.e it must provide endpoints `/encode_sents` and
      `/cosim_to_pred_score`
    :returns: a vecspace encoder dict with keys
      `sentence_encoder_fn` with a function that accepts a list of str
        sentences and returns a list of embeddings.
      `cosim2preds_fn` with a function that accepts a list of cosine
        similarities and returns a list of semantic similarity predictions.
    :rtype: dict
    """
    return {
        'sentence_encoder_fn': semantic_sent_encoder(semencoder_url),
        'cosim2preds_fn': semantic_cosim2preds(semencoder_url),
        'semantic_encoder_info_fn': semantic_sent_encoder_info(semencoder_url),
        'semantic_encoder_url': semencoder_url
    }


def load_tsv_vector_space(tsv_vecs_path, sep='\t'):
    """load the word embeddings file and create a vecspace dict
    that stores vectors with their correlated information and
    indices useful for searching the spece.

    :param tsv_vecs_path: path to upload the stored embeddings
    :type tsv_vecs_path: str
    :param sep: separator of the embeddings file
    :type sep: str
    :return: dictionary that contains the embeddings `labels`, the numpy array
    of word `vectors`, the created `faiss_index`, the `source` path
    of the embeddings and the number of embeddings dimensions `dim`
    :rtype: dict
    """
    labels = []
    vectors = []
    start = time.time()
    logger.info('Loading vectors from %s' % tsv_vecs_path)
    ndims = None
    with open(tsv_vecs_path, 'r', encoding='utf-8') as vecs_f:
        for line_idx, line in enumerate(vecs_f.readlines()):
            elems = line.split(sep)
            labels.append(elems[0])
            if ndims is None:
                ndims = len(elems[1:])
            msg = 'line %d, expecting %d dims, but %d' % (
                line_idx, ndims, len(elems[1:]))
            assert ndims == len(elems[1:]), msg
            vectors.append(np.array(list(map(float, elems[1:])),
                                    dtype=np.float32))
        vectors = np.vstack(vectors)

        labels_set = set(labels)
        if len(labels_set) != len(labels):
            logger.warn("Repeated labels, %d vs %d" % (
                len(labels), len(labels_set)))
        ndims = vectors.shape[1]
        assert ndims == ndims, '%d != %d' % (ndims, ndims)
    logger.info('Loaded %d vectors in %ds' % (
        len(labels), (time.time() - start)))
    nvectors = normalize(vectors)
    return {'labels': labels,
            'vectors': nvectors,
            'faiss_index': create_faiss_index(nvectors, ndims),
            'source': tsv_vecs_path,
            'dim': ndims,
            'dataset_info': {
                '@context': 'http://schema.org',
                '@type': 'Dataset',
                'name': 'Co-inform Sentence embeddings',
                'identifier': hashu.sha256_file(tsv_vecs_path),
                'description': 'Dataset of %d sentence embeddings extracted from claim reviews and articles collected as part of the Co-inform project' % len(labels),
                'dateCreated': isodate.as_utc_timestamp(os.path.getctime(tsv_vecs_path)),
                'dateModified': isodate.as_utc_timestamp(os.path.getmtime(tsv_vecs_path)),
                'creator': bot_describer.esiLab_organization(),
                'encoding': {
                    '@type': 'MediaObject',
                    'contentSize': bot_describer.readable_file_size(tsv_vecs_path),
                    'encodingFormat': 'text/tab-separated-values'
                }
            }}
