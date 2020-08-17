#
# Copyright (c) 2020 Expert System Iberia
#
"""Provides normalisation of a tree of schema.org compliant items into
a dict of identifiers to relatively flat items with references between
each other.
"""
import copy
import logging
from acred import content
from esiutils import dictu, hashu


logger = logging.getLogger(__name__)


def normalise_nested_item(tree, cfg):
    """Converts a nested data item into an index dict

    :param tree: a nested data item
    :param cfg: config options
    :returns: an ident dict containing identifiers as the keys and
      relatively flat items as the values. The dict will also contain
      a special key `mainItem` which has as a value the main
      identifier string for the input tree
    :rtype: dict
    """
    assert content.is_item(tree)
    logger.debug('extracting item and linked items from %s' % (list(tree.keys())))
    ident_tree = ensure_ident(tree, cfg)
    ident2items = index_ident_tree(ident_tree, cfg)
    result = {k: item_with_refs(v, cfg) for k, v in ident2items.items()}
    return {**result,
            'mainItem': get_item_identifiers(ident_tree, cfg)[0]}

def nested_item_as_graph(tree, cfg):
    """Converts a nested data item into a graph dict

    :param tree: a nested data item
    :param cfg: config options
    :returns: a graph dict with fields "nodes" and "links"
    :rtype: dict
    """
    assert content.is_item(tree)
    logger.debug('extracting item and linked items from %s' % (list(tree.keys())))
    ident_tree = ensure_ident(tree, cfg)
    ident2items = index_ident_tree(ident_tree, {**cfg,
                                                'unique_id_index': True})
    
    node_links_tuples = [item_and_links(v, cfg) for k, v in ident2items.items()]
    nodes = [n for n, links in node_links_tuples]
    if 'ensureUrls' in cfg:
        nodes = [ensure_url(n, cfg) for n in nodes]
    links = [link for n, links in node_links_tuples
             for link in links]
    return {'@context': 'http://coinform.eu',
            '@type': 'Graph',
            'nodes': nodes,
            'links': links,
            'mainNode': get_item_identifiers(ident_tree, cfg)[0]}
    

def trim_tree(tree, prop, depth):
    """Trims a newted data item to limit number of a nested property

    :param tree: a nested data item or a list of such items
    :param prop: the property to trim. It is assumed that values of
    property are either a single nested data item or a list of nested
    data items.
    :param depth: int maximum number of property jumps to follow from tree
    :returns: a trimmed version of the input tree
    :rtype: dict or list of dicts
    """
    assert type(prop) is str, '%s: %s' % (type(prop), prop)
    if type(depth) is not int or depth < 0:
        raise ValueError('depth %s' % (depth))

    if type(tree) is list:
        return [trim_tree(sub, prop, depth) for sub in tree]
    if not content.is_item(tree):
        return tree

    if prop not in tree:
        return tree
        
    result = {**tree}
    if depth == 0:
        del result[prop]
    else:  # depth > 0
        result[prop] = trim_tree(result[prop], prop, depth - 1)
    return  result
    

def filter_ident_index_by_type(ident_index, qtypes):
    """Filter an ident_index selecting only entries matching the query types

    :param ident_index: 
    :param qtypes: a single typename or a list of typenames to match
    :returns: 
    :rtype: 
    """
    if type(qtypes) is str:
        return filter_ident_index_by_type(ident_index, [qtypes])
    assert type(qtypes) is list
    return {k: v
            for k, v in ident_index.items()
            if content.is_item(v) and content.item_matches_type(v, qtypes)}

def partition_ident_index(ident_index, partition_types):
    """Creates an index partitioned by types

    :param ident_index: an identity item index; i.e. a dict with
      identifiers as keys and data items as values
    :param partition_types: a dict specifying the partition labels and
      types to include in each partition. The dict must have strings
      as keys and list of type names as values. We assume that the
      types are disjoint.
    :returns: a partitioned index. This is a dict with as keys the
      label for each partition and as values a subset of the input
      `ident_index`. An invariant is that merging all the values in
      the result yields the same as `ident_index`
    :rtype: dict
    """
    assert type(partition_types) is dict
    assert '_rest' not in partition_types, 'partition label _rest is reserved'
    result = {plabel: {}
              for plabel, pqtypes in partition_types.items()}
    result['_rest'] = {}
    for ident, item in ident_index.items():
        if content.is_item(item):
            matching_plabels = [
                partition_label
                for partition_label, partition_qtypes in partition_types.items()
                if content.item_matches_type(item, partition_qtypes)]
            if len(matching_plabels) > 1:
                logger.warning('Multiple partitions match item %s: %s' % (ident, matching_plabels))
                result[matching_plabels[0]][ident] = item
            elif len(matching_plabels) == 1:
                result[matching_plabels[0]][ident] = item
            else:
                result['_rest'][ident] = item
    return result

    
def index_ident_tree(tree, cfg):
    """Converts a tree item into an index dict

    :param tree: a possibly nested value data structure which may
      contain data items. All data items must have an identifier or
      other identifying field.
    :param cfg: configuration options
    :returns: an identifier index for the tree; it contains identifier
      strings as keys and branches of the input tree as values. Note
      that the tree and its branches are not modified at all. For a
      more trimmed index, you may want to map the values using the
      `item_with_refs` method.
    :rtype: dict
    """
    if type(tree) is list:
        result = {}
        for it in tree:
            result = _index_merge(result, index_ident_tree(it, cfg), cfg)
        return result
    elif type(tree) is dict:
        result = {}
        # first build index for any nested values
        for k, v in tree.items():
            if k in cfg.get('composite_rels', []):
                continue
            result = _index_merge(result, index_ident_tree(v, cfg), cfg)
        # finally, add entries for this item if it's an identifiable type
        if content.is_item(tree) and tree['@type'] not in no_ident_types:
            ids = get_item_identifiers(tree, cfg)
            assert len(ids) > 0, 'Cannot index an item without identifiers'
            if cfg.get('unique_id_index', False):
                ids = ids[:1] # keep only the first id
            for idval in ids:
                assert type(idval) == str
                result = _index_merge(result, {idval: tree}, cfg)
        return result
    else: # assume simple values, these are never indexed
        return {} 


def _index_merge(idx_a, idx_b, cfg):
    validate_is_item_index(idx_a)
    validate_is_item_index(idx_b)
    
    shared_keys = set(idx_a.keys()) & set(idx_b.keys())
    if len(shared_keys) == 0:
        return {**idx_a, **idx_b}
    else:
        result = {**idx_a, **idx_b}
        for k in shared_keys:
            result[k] = {**idx_a[k], **idx_b[k]}
        return result


def validate_is_item_index(idx):
    if type(idx) is not dict:
        raise ValueError('Object is not an item index. It must be a dict, not %s' % (type(idx)))
    if len(idx) == 0: # empty indices are OK
        return True
    key_types = list(set([type(k) for k in idx.keys()]))
    if key_types != [str]:
        raise ValueError('At least one key is not a string %s' % (list(idx.keys())))
    val_types = list(set([type(v) for k, v in idx.items()]))
    if val_types != [dict]:
        raise ValueError('At least one value is not a dict')
    return True

# list of types which do not require an ident
no_ident_types = ['MediaObject', 'Timing', "schema:Language", "Thing",
                  "schema:CreativeWork", 'CreativeWork',
                  'nif:String', 'schema:Rating', 'schema:ClaimReview', 'ClaimReview']
no_url_types = no_ident_types + ['Dataset', 'SentencePair']

def ensure_ident(item, cfg):
    """Creates a copy of the input tree whereby all the items have a unique identifier

    :param item: a datastructure nested schema.org compatible item
    :param cfg: config options
    :returns: a copy of tree but any item and subitem in the tree has
      a unique identifier field
    :rtype: any
    """
    if type(item) == list:
        return [ensure_ident(it, cfg) for it in item]
    if type(item) == dict:
        assert dictu.is_value(item)
        result = {k: ensure_ident(v, cfg) for k, v in item.items()}
        if content.is_item(result):
            if 'identifier' in item:
                return result
            elif item['@type'] in no_ident_types:
                return result
            else:
                return {**result,
                        'identifier': calc_identifier(result, cfg)}
        else: # no ident is needed
            return {**item}
    # all other types are returned as they are
    return item

def ensure_url(item, cfg):
    """Creates a copy of the input tree whereby all the items have a url value

    :param item: a datastructure nested schema.org compatible item
    :param cfg: config options
    :returns: a copy of tree but any suitable item and subitem in the tree has
      a url field
    :rtype: any
    """
    if type(item) == list:
        return [ensure_url(it, cfg) for it in item]
    if type(item) == dict:
        assert dictu.is_value(item)
        result = {k: ensure_url(v, cfg) for k, v in item.items()}
        if content.is_item(result):
            if 'url' in item:
                # optionally, make sure it matches the calculated url
                #  if not a match, replace url value and put old value in sameAs?
                return result
            elif item['@type'] in no_url_types:
                return result
            else:
                return {**result,
                        'url': calc_item_url(result, cfg)}
        else: # no ident is needed
            return {**item}
    # all other types are returned as they are
    return item

def calc_identifier(item, cfg):
    """Given a data item, calculate its identifier

    Any nested items must already have an identifier.

    The default identifier is given by a subset of its fields.

    :param item: The item for which to calculate the identifier
    :param cfg: config options
    :returns: a unique identifier within acred.
    :rtype: str
    """
    assert content.is_item(item)
    assert 'identifier' not in item
    to_id = item_with_refs(dictu.select_keys(item, ident_keys(item, cfg)), cfg)
    return hashu.hash_dict(to_id)

def calc_item_url(item, cfg):
    """Given a data item, calculate its url

    The url is calculated based on 

    :param item: 
    :param cfg: 
    :returns: 
    :rtype: 

    """
    assert content.is_item(item)
    #assert 'identifier' in item
    template = route_template(item, cfg)
    if template is not None:
        return '%s%s' % (content.ci_context, template.format(**item))
    else:
        return None

def build_index_type_histo(ident_index):
    """Given an identifier index, return a histogram of types and counts

    :param ident_index: a dict with identifiers as keys and data items as values
    :returns: a histogram of types, i.e. a dict with declared types as keys and counts as values
    :rtype: dict
    """
    result = {}
    for k, v in ident_index.items():
        if type(v) is dict:
            itype = v.get('@type', None)
            if itype:
                prev = result.get(itype, 0)
                result[itype] = prev + 1
    result = {k: v for k, v in sorted(result.items(), key=lambda item: -item[1])}
    return result

def item_and_links(item, cfg):
    """Returns a copy of item where all nested items have been converted into a list of link

    :param item: a (nested) item
    :param cfg: config options. In particular option
      `composite_rels` specifies a list of relation names which should not be decomposed.
    :returns: a tuple where the first item is the item without any refs, nor nested items
    :rtype: tuple
    """
    def value_as_links(v, src_id, rel):
        if rel in cfg.get('composite_rels', []):
            return None
        if type(v) is list:
            return [link  for sv in v
                    if value_as_links(sv, src_id, rel) is not None
                    for link in value_as_links(sv, src_id, rel)]
        if content.is_item(v) and v['@type'] not in no_ident_types:
            ids = get_item_identifiers(v, cfg)
            if len(ids) > 0:
                return [{'source': src_id,
                        'target': ids[0],
                        'rel': rel}]
            else:
                raise ValueError('Nested item does not have an identifier %s' % (v))
        elif type(v) is dict:
            if bool(cfg.get('debug_identifiers', False)) and has_identifier(v, cfg):
                logger.debug('Nested dict value has identifier or url, but no @type %s' % (v))
            return None
        elif v is None:
            return v
        else:
            assert type(v) in [int, float, str, bool], 'Unsupported value type %s %s for %s in %s' % (
                type(v), v, src_id, item)
            return None

    src_id = get_item_identifiers(item, cfg)[0]
    assert content.is_item(item), 'Expecting an item. @type field not included? %s' % (item)
    return {k: v for k, v in item.items()
            if value_as_links(v, src_id, k) is None}, [
                    link for k, v in item.items()
                    if value_as_links(v, src_id, k) is not None
                    for link in value_as_links(v, src_id, k)]
    

def item_with_refs(item, cfg):
    """Returns a copy of item where all nested items have been replaced by refs

    :param item: a (nested) item 
    :returns: a copy of the input item, where all nested items have
      been replaced by refs. It is assumed that all nested items
      already have either an `identifier` field or a `url` field which
      will serve as the reference.
    :rtype: dict
    """
    def value_as_ref(v, for_k=None):
        if type(v) is list:
            return [value_as_ref(sv, for_k) for sv in v]
        if content.is_item(v) and v['@type'] not in no_ident_types:
            ids = get_item_identifiers(v, cfg)
            if len(ids) > 0:
                return ids[0] # return the first (main) identifier
            else:
                raise ValueError('Nested item does not have an identifier %s' % (v))
        elif type(v) is dict:
            if bool(cfg.get('debug_identifiers', False)) and has_identifier(v, cfg):
                logger.debug('Nested dict value has identifier or url, but no @type %s' % (v))
            return {**v}
        elif v is None:
            return v
        else:
            assert type(v) in [int, float, str, bool], 'Unsupported value type %s %s for %s in %s' % (
                type(v), v, for_k, item)
            return v

    if not content.is_item(item):
        logger.warn('Expecting an item. @type field not included? %s' % (item))
    assert type(item) is dict, '%s' (type(item))
    return {k: value_as_ref(v, k) for k, v in item.items()}

def get_item_identifiers(item, cfg):
    # list of identifier fields, values assumed to be single str
    #  the order is important!!
    return [item[idk] for idk in ['identifier', '@id', 'url']
            if idk in item]

def has_identifier(item, cfg):
    return len(get_item_identifiers(item, cfg)) > 0
        

def ident_keys(item, cfg):
    """Returns the list of keys in item which gives its identity

    :param item: dict with type information
    :param cfg: config options
    :returns: a list of fields for item that give it its identity
    :rtype: list
    """
    try:
        return content.ident_keys(item)
    except Exception as e:
        logger.error('Failed to extract ident keys for %s' % (item), e)
        raise e

def route_template(item, cfg):
    """Returns the route for a data item.

    :param item: 
    :param cfg: 
    :returns: a "new style" python string template. see
      https://docs.python.org/3/library/stdtypes.html#str.format
    :rtype: str
    """
    return content.route_template(item)
