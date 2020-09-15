#
# Copyright (c) 2020 Expert System Iberia
#
"""
"""
import requests
import json
from colorama import init, Fore



def test_check_worthiness():
    check_worthiness_url = 'http://localhost:8073/worthinesschecker/predict_worthiness'
    test_claims = {'sentences': ['A typical family of four making $75,000 will see their tax bill reduced by $2,000, slashing their tax bill in half.',
                                 'the coronavirus is a bioweapon',
                                 'We eliminated an especially cruel tax that fell mostly on Americans making less than $50,000 a year, forcing them to pay tremendous penalties simply because they couldn’t afford government-ordered health plans.',
                                 'We slashed the business tax rate from 35 percent all the way down to 21 percent, so American companies can compete and win against anyone else anywhere in the world.',
                                 'Toyota and Mazda are opening up a plant in Alabama — a big one.',
                                 ]}
    headers = {'Content-type': 'application/json'}
    response = requests.post(check_worthiness_url, json.dumps(test_claims), headers=headers,
                             verify=False)
    if str(response) == '<Response [200]>':
        print(Fore.GREEN + 'Tweet claim credibility endpoint: OK')
        print(Fore.GREEN + 'Response: %s' % response)
        print(Fore.RESET)
    else:
        print(Fore.RED + 'Tweet claim credibility endpoint: ERRROR')
        print(Fore.RED + 'Response: %s' % response)
        print(Fore.RESET)

    print(response.text)



def test_tweet_claim_credibility():
    tweet_claim_credibility_url = 'http://localhost:8070/test/api/v1/tweet/claim/credibility'
    # print('tweet claim credibility url: ', tweet_claim_credibility_url)
    test_tweets = {
        "tweets":
            [
                {
                    "tweet_id": 1178504740558163968,
                    "content": "Spirit kills coronavirus. This is the best treatment"
                },
                {
                    "tweet_id": 1178504740558163968,
                    "content": "covid-19 is a bioweapon"
                }
            ]
    }
    auth = requests.auth.HTTPBasicAuth('testuser', 'testpass')
    headers = {'Content-type': 'application/json'}
    response = requests.post(tweet_claim_credibility_url, json.dumps(test_tweets), headers=headers, auth=auth,
                             verify=False)
    print(response.text)
    if str(response) == '<Response [200]>':
        print(Fore.GREEN + 'Tweet claim credibility endpoint: OK')
        print(Fore.GREEN + 'Response: %s' % response)
        print(Fore.RESET)
    else:
        print(Fore.RED + 'Tweet claim credibility endpoint: ERRROR')
        print(Fore.RED + 'Response: %s' % response)
        print(Fore.RESET)



if __name__ == '__main__':
    init()
    test_tweet_claim_credibility()
