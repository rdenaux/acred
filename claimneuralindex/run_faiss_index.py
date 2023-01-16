import numpy as np
import time
import faiss
import logging
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

claim_embeddings = '/opt/data/model/claim-embeddings/claim_embs.tsv'

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


def load_tsv_vector_space(tsv_vecs_path, sep='\t'):
    labels = []
    vectors = []
    start = time.time()
    logger.info('Loading vectors from %s' % tsv_vecs_path)
    ndims = None
    with open(tsv_vecs_path, 'r', encoding='utf-8') as vecs_f:
        for line_idx, line in enumerate(vecs_f.readlines()):
            elems = line.split(sep)
            #print('Line %d (%d chars) has %d elements' % (line_idx, len(line), len(elems)))
            labels.append(elems[0])
            if ndims is None:
                ndims = len(elems[1:])
            assert ndims == len(elems[1:]), 'line %d, expecting %d dims, but %d' % (
                line_idx, ndims, len(elems[1:]))
            vectors.append(np.array(list(map(float, elems[1:])), dtype=np.float32))
        vectors = np.vstack(vectors)

        labels_set = set(labels)
        if len(labels_set) != len(labels):
            logger.warn("Repeated labels, %d vs %d" % (len(labels), len(labels_set)))
        indices = {l: i for i, l in enumerate(labels)}
        ndims = vectors.shape[1]
        assert ndims == ndims, '%d != %d' % (ndims, ndims)
    logger.info('Loaded %d vectors in %ds' % (len(labels), (time.time() - start)))
    nvectors = normalize(vectors)
    return {'labels': labels,
            'vectors': nvectors,
            'source': tsv_vecs_path,
            'dim': ndims}


vec_space = load_tsv_vector_space(claim_embeddings)

logger = logging.getLogger(__name__)

vecs = vec_space['vectors']
dims = vec_space['dim']                  # dimension
len_vecs = len(vec_space['vectors'])        # database size
num_queries = 1000                        # len_vecs of queries
k_nn = 1                            # number of nearest neighbors
nlist = 85                       # optimization cells

train, test = train_test_split(range(len_vecs), test_size=num_queries/len_vecs)
train_vecs = vecs[train]
test_vecs = vecs[test]
print('train sample: ', len(train_vecs))
print('test sample: ', len(test_vecs))


quantizer = faiss.IndexFlatIP(dims)
index = faiss.IndexIVFFlat(quantizer, dims, nlist, faiss.METRIC_INNER_PRODUCT)
assert not index.is_trained
index.train(train_vecs)
assert index.is_trained
index.add(train_vecs)

start = time.time()
ivf_sims, ivf_index = index.search(test_vecs, k_nn)
end = time.time()

print("IndexIVFFlat elapsed time during searching in seconds:", end-start)

index2 = faiss.IndexFlatIP(dims)
index2.add(train_vecs)

start = time.time()
ip_sims, ip_index = index2.search(test_vecs, k_nn)
end = time.time()

print("IndexFlatIP elapsed time during searching in seconds:", end-start)

count = np.sum(ivf_index!=ip_index)
perc = (count*100)/(num_queries*k_nn)
print("FAILURE PERCENTAGE: " + str(perc) + "%")