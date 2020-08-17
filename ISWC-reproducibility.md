# ISWC reproducibility

This document describes how to use `acred` to reproduce the results described in our paper at [ISWC'20](https://iswc2020.semanticweb.org/)

Reproducibility limitation: some of code in the version of `acred` we used during experimentation relied on proprietary code from Expert System which had to be removed from the code released. This code is used during the analysis of long texts like articles, as it identifies sentences which may be claims based on its relevance to topics and the presence of named entities. We plan to replace this code with sentence detection via NLTK and a custom checkworthiness detection model. This should mainly affect results on `FakeNewsNet` (articles), but not `Clef'18` (claims) or `coinform250` (tweets, most of which do not contain links to other web pages**.

Currently, this document is still work-in-progress, but in the next few days (August 2020) we plan to release:
* the acred code
* the evaluation database of claims as:
** a list of 40K extracted sentences and URLs where they were extracted; 
** a list of 45K claims from ClaimReviews and URLs to where they were extracted; 
* instructions for configuring acred and calling required external services
* scripts for executing acred on the evaluation datasets
* JSON-LD files for all the CRs generated for the evaluation datasets; 
* link to the coinform250 dataset on GitHub; 
* jupyter notebooks for the sentence encoder and stance detection components
* additional code for collecting ClaimReviews 


