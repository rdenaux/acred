import requests

base_url = 'https://tweetstore.coinform.eu'


def tweet(tweet_id):
    _type = type(tweet_id)
    assert _type in [int]
    url = base_url + '/tweet/%d' % tweet_id
    resp = requests.get(url)
    if resp.ok:
        return resp.json()
    return None


def put_tweet(tweet):
    def validate_tweet(t):
        assert 'tweet_id' in tweet

    assert type(tweet) in [dict, list]
    if type(tweet) == dict:
        tweet = [tweet]
    for t in tweet:
        validate_tweet(t)

    url = base_url + '/tweet'
    resp = requests.put(url, json=tweet)
    return resp
