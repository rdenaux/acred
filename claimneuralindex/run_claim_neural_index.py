import requests
import json
import urllib

sents = ['Donald Trump is a liar']

auth_user = 'testuser'
auth_pass = 'testpass'

claim_search_url = 'http://localhost:8070/test/api/v1/claim/search'
search_params = 'index_format=faiss&' + "&".join(["claim=%s" % urllib.parse.quote(sent) for sent in sents])
print(search_params)
search_verify = True
auth = requests.auth.HTTPBasicAuth(auth_user, auth_pass)

response = requests.get("%s?%s" % (claim_search_url, search_params), verify=search_verify, auth=auth)
print(response)