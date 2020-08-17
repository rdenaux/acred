#
# Copyright (c) 2020 Expert System Iberia
#
"""
Unit Tests for itemnorm.py
"""
import pytest
import json
from acred import itnorm

def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

aggqsentReview01 = read_json('test/AggQSentCredReview/Clef18_Train_Task2-English-1st_Presidential1.json')
sentStanceRev05 = read_json('test/SentStanceReview/ssr05.json')

def test_normalise_nested_item():
    identd = itnorm.normalise_nested_item(aggqsentReview01, {})
    # with open('test/AggQSentCredReview/Clef18_Train_Task2-English-1st_presidential1_norm.json', 'w') as outf:
    #     json.dump(identd, outf, indent=2)
    assert len(identd) == 113
    type_cnt = itnorm.build_index_type_histo(identd)
    assert len(type_cnt) == 26
    print('types by cnt', type_cnt)

    parted_index = itnorm.partition_ident_index(identd, {
        'Bot': ['Bot'],
        'Rating': ['Rating', 'AggregateRating'],
        'Review': ['Review', 'SentSimilarityReview', 'WebSiteCredReview'],
        'CreativeWork': ['Sentence', 'Article', 'WebSite'],
        'Organization': ['Organization', "schema:Organization"],
        'SentencePair': ['SentencePair']
    })
    
    bot_d = parted_index['Bot']
    assert len(bot_d) == 15  # 15 of the 113 are Bots
    rating_d = parted_index['Rating']
    assert len(rating_d) == 34 # 34 of the 113 are Ratings
    review_d = parted_index['Review']
    assert len(review_d) == 33 # 33 of the 113 are Reviews
    content_d = parted_index['CreativeWork']
    assert len(content_d) == 19 # 19 of the 113 are contents
    sent_pairs_d = parted_index['SentencePair']
    assert len(sent_pairs_d) == 5 # (total 97)
    org_d = parted_index['Organization']
    assert len(org_d) == 5
    other_d = parted_index['_rest']
    print('Upartitioned item types', itnorm.build_index_type_histo(other_d))
    assert len(other_d) == 1 # only Dataset

def test_nested_item_as_graph_01():
    graph = itnorm.nested_item_as_graph(aggqsentReview01, {})
    # with open('test/AggQSentCredReview/Clef18_Train_task2-English-1st_presidential1_graph.json', 'w') as outf:
    #     json.dump(graph, outf, indent=2)
    assert len(graph['nodes']) == 101
    assert len(graph['links']) == 157

def test_nested_item_as_graph_02():
    # same as case 01, but now we keep items `reviewRating` as part of the parent item
    graph = itnorm.nested_item_as_graph(aggqsentReview01, {'composite_rels': ['reviewRating']})
    # with open('test/AggQSentCredReview/Clef18_Train_task2-English-1st_presidential1_graph02.json', 'w') as outf:
    #     json.dump(graph, outf, indent=2)
    assert len(graph['nodes']) == 71
    assert len(graph['links']) == 124
    mainNode_id = graph['mainNode']
    mainNode = [n for n in graph['nodes'] if n.get('identifier') == mainNode_id][0]
    expectedKeys = ['@context', '@type', 'dateCreated', 'identifier', 'reviewRating']
    assert set(expectedKeys) == set(list(mainNode.keys()))

def test_nested_item_as_graph_03():
    # same as case 02, but now we keep ensure returned items are assigned URLs
    graph = itnorm.nested_item_as_graph(aggqsentReview01, {'composite_rels': ['reviewRating'],
                                                           'ensureUrls': True})
    # with open('test/AggQSentCredReview/Clef18_Train_task2-English-1st_presidential1_graph02.json', 'w') as outf:
    #     json.dump(graph, outf, indent=2)
    assert len(graph['nodes']) == 71
    assert len(graph['links']) == 124
    mainNode_id = graph['mainNode']
    mainNode = [n for n in graph['nodes'] if n.get('identifier') == mainNode_id][0]
    expectedKeys = ['@context', '@type', 'dateCreated', 'identifier', 'reviewRating', 'url']
    assert set(expectedKeys) == set(list(mainNode.keys()))

def test_ensure_ident_01():
    ssr05_id = itnorm.ensure_ident(sentStanceRev05, {})
    assert 'identifier' not in sentStanceRev05
    assert 'identifier' in ssr05_id

    
def test_ensure_ident_02():
    aqsr01_id = itnorm.ensure_ident(aggqsentReview01, {})
    assert 'identifier' not in aggqsentReview01
    assert 'identifier' in aqsr01_id
    # assert aqsr01_id == aggqsentReview01
    
    
def test_item_with_refs_01():
    actual = itnorm.item_with_refs({
        '@type': 'TestItem',
        'a': {'@type': 'NestedItemA',
            'identifier': 'a1'},
        'b': [{'@type': 'NestedItemB',
               'identifier': 'b1'},
              {'@type': 'NestedItemC',
               'identifier': 'c1'}]
    }, {})
    expected = {'@type': 'TestItem',
                'a': 'a1',
                'b': ['b1', 'c1']}
    assert expected == actual


def test_item_with_refs_02():
    actual = itnorm.item_with_refs({
        '@type': 'TestItem',
        'a': {'@type': 'NestedItemA',
            'identifier': 'a1'},
        'b': [{'@type': 'NestedItemB',
               'url': 'http://example.com/b1'},
              {'@type': 'NestedItemC',
               'identifier': 'c1'}]
    }, {})
    expected = {'@type': 'TestItem',
                'a': 'a1',
                'b': ['http://example.com/b1', 'c1']}
    assert expected == actual


def test_item_with_refs_03():
    actual = itnorm.item_with_refs({
        '@type': 'TestItem',
        'a': {'identifier': 'a1'},
        'b': [{'@type': 'NestedItemB',
               'identifier': 'b1'},
              {'@type': 'NestedItemC',
               'identifier': 'c1'}]
    }, {})
    expected = {'@type': 'TestItem',
                # nested dict without @type are considered plain dicts
                'a': {'identifier': 'a1'}, 
                'b': ['b1', 'c1']}
    assert expected == actual


def test_item_with_refs_04():
    with pytest.raises(ValueError) as excinfo:
        itnorm.item_with_refs({
            '@type': 'TestItem',
            'a': {'identifier': 'a1'},
            'b': [{'@type': 'NestedItemB',
                   'identifier': 'b1'},
                  {'@type': 'NestedItemC',
                   'non_identifier': 'x'
                  }]
        }, {})
    assert 'Nested item does not have an identifier' in str(excinfo.value)
    
    
def test_index_merge_01():
    with pytest.raises(ValueError) as excinfo:
        itnorm._index_merge("a", {'a': 'b'}, {})
    assert 'Object is not an item index. It must be a dict' in str(excinfo.value)

def test_index_merge_02():
    merged = itnorm._index_merge(
        {'id1': {'a': 'a'}},
        {'id2': {'b': 'b'}}, {})
    expected = {
        'id1': {'a': 'a'},
        'id2': {'b': 'b'}}
    assert expected == merged

def test_index_merge_03():
    merged = itnorm._index_merge(
        {'id1': {'a': 'a'}},
        {'id1': {'b': 'b'}}, {})
    expected = {
        'id1': {'a': 'a',
                'b': 'b'}}
    assert expected == merged


def test_index_merge_04():
    with pytest.raises(ValueError) as excinfo:
        merged = itnorm._index_merge(
            {'id1': {'a': 'a'}},
            {'id1': 'a'},  # value is not a dict!!
            {})
    assert 'At least one value is not a dict' in str(excinfo.value)
    
    
def test_trim_tree_01():
    tree = {
        '@type': 'a',
        'sub': {
            '@type': 'b',
            'sub': {
                '@type': 'c',
                'sub': {
                    '@type': 'd'}
            }}}

    trimmed_0 = itnorm.trim_tree(tree, 'sub', 0)
    expect_0 = {
        '@type': 'a'}
    assert expect_0 == trimmed_0

    
    trimmed_1 = itnorm.trim_tree(tree, 'sub', 1)
    expect_1 = {
        '@type': 'a',
        'sub': {
            '@type': 'b'}}
    assert expect_1 == trimmed_1

    trimmed_2 = itnorm.trim_tree(tree, 'sub', 2)
    expect_2 = {
        '@type': 'a',
        'sub': {
            '@type': 'b',
            'sub': {
                '@type': 'c'}}}
    assert expect_2 == trimmed_2

    assert tree == itnorm.trim_tree(tree, 'sub', 3)
    assert tree == itnorm.trim_tree(tree, 'sub', 4)

    assert tree == itnorm.trim_tree(tree, 'someProp', 0)

    with pytest.raises(ValueError) as excinfo:
        itnorm.trim_tree(tree, 'sub', -1)
    assert 'depth' in str(excinfo.value)



def test_trim_tree_02():
    tree = {
        '@type': 'a',
        'sub': [{ # first
            '@type': 'b',
            'sub': {
                '@type': 'c',
                'sub': {
                    '@type': 'd'}
            }}, { # second 
                '@type': 'b2',
                'sub': {
                    '@type': 'c2',
                    'sub': {
                        '@type': 'd2'}
                }}]}

    trimmed_0 = itnorm.trim_tree(tree, 'sub', 0)
    expect_0 = {
        '@type': 'a'}
    assert expect_0 == trimmed_0

    
    trimmed_1 = itnorm.trim_tree(tree, 'sub', 1)
    expect_1 = {
        '@type': 'a',
        'sub': [{
            '@type': 'b'},
                {'@type': 'b2'}
        ]}
    assert expect_1 == trimmed_1

    trimmed_2 = itnorm.trim_tree(tree, 'sub', 2)
    expect_2 = {
        '@type': 'a',
        'sub': [{
            '@type': 'b',
            'sub': {
                '@type': 'c'}},
                {
                    '@type': 'b2',
                    'sub': {
                        '@type': 'c2'}}
        ]}
    assert expect_2 == trimmed_2

    assert tree == itnorm.trim_tree(tree, 'sub', 3)
    assert tree == itnorm.trim_tree(tree, 'sub', 4)

    assert tree == itnorm.trim_tree(tree, 'someProp', 0)

    with pytest.raises(ValueError) as excinfo:
        itnorm.trim_tree(tree, 'sub', -1)
    assert 'depth' in str(excinfo.value)    
