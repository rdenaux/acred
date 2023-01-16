# Worthiness Checker

This is a service created to check the worthiness of a sentence (or a collection of sentences) in order to select factual statements and ignoring sentences which are not fact-checkable or check-worthy. This module will allow to execute the acred pipeline overcoming bottlenecks due of a big amount of unverifiable claims.

# How to run the service
It is possible to run this service:
* through ``Docker-compose``
* standalone with this python command ``$ python runsrv.py -service worthinesschecker``

# Make a request to the service
To use this service make a POST request both with a string or a list of strings:
```
curl -H "Content-Type: application/json" -X POST -d "{'sentences': 'Vaccines cause autism'}" http://host:port-mapped/worthinesschecker/predict_worthiness
```
```
curl -H "Content-Type: application/json" -X POST -d "{'sentences': ['Vaccines cause autism', 'I love beer and open source']}" http://host:port-mappe/worthinesschecker/predict_worthiness
 ```

 In particular, the service assigns for each sentence a worthy label (CFS) or an unworhy label (NCS) and a confidence value. To each sentence processed by the service an ID is assigned. The Worthiness Checker Review contains several details, including information about the Transformer model used to make predictions.

 This is an example of the Worthiness checker Review response:

```

{
  "meta": {
    "model_info": {
      "@context": "http://coinform.eu",
      "@type": "CheckWorthinessReviewer",
      "additionalType": [
        "SoftwareApplication",
        "Bot"
      ],
      "applicationCategory": [
        "NLP"
      ],
      "applicationSubCategory": [
        "Check-worthiness"
      ],
      "applicationSuite": [
        "Co-inform"
      ],
      "author": {
        "@type": "Organization",
        "name": "Expert System Iberia Lab",
        "url": "http://expertsystem.com"
      },
      "dateCreated": "2020-05-08T15:18:00Z",
      "description": "Assesses the worthiness of a sentence: CFS (whorty) NCS (unwhorty). It was trained and evaluated on a group of different datasets (CBD+Poynter+Clef'19T1) achieving 95% accuracy.",
      "executionEnvironment": {
        "cuda": false,
        "hostname": "FMERENDA-NB",
        "python.version": "3.6.9"
      },
      "identifier": "Sz4MNWEdIu8zl5chh2rCYQsSuBlRDtS8uuy5gyl2M-0",
      "isBasedOn": [],
      "launchConfiguration": {
        "model": {
          "base_model": "roberta-base",
          "batch_size": 64,
          "class": "transformers.RobertaForSequenceClassification",
          "finetuned_from_layer": 8,
          "isBasedOn": [
            "transformers=2.8.0"
          ],
          "label2i": {
            "CFS": 1,
            "NCS": 0
          },
          "loss": "torch.nn.CrossEntropyLoss",
          "seq_len": 128,
          "train_val_result": {
            "loss": 0.11967675889340731,
            "metrics": {
              "acc": 0.9553752535496958,
              "confusion_matrix": [
                [
                  352,
                  77
                ],
                [
                  33,
                  2003
                ]
              ],
              "confusion_matrix_norm": [
                [
                  0.8205128205128205,
                  0.1794871794871795
                ],
                [
                  0.016208251473477406,
                  0.9837917485265226
                ]
              ],
              "f1_weighted": 0.9544076983742505,
              "n": 2465,
              "prec_micro": 0.9553752535496958,
              "recall_micro": 0.9553752535496958
            }
          }
        },
        "model_config": {
          "@type": "MediaObject",
          "contentSize": "481 B",
          "dateCreated": "2020-05-13T15:45:32.230276Z",
          "dateModified": "2020-05-08T02:48:12.163000Z",
          "name": "config.json",
          "sha256Digest": "ef0185e2aae6e06c5f105a285006952c340e20c7dbf43c86ec82601b13fc45e9"
        },
        "pytorch_model": {
          "@type": "MediaObject",
          "contentSize": "477.79 MB",
          "dateCreated": "2020-05-13T15:45:32.271233Z",
          "dateModified": "2020-05-08T03:28:05.299000Z",
          "name": "pytorch_model.bin",
          "sha256Digest": "d203ea8936fd59e26723e35584b65560f872f3baef0afd6c6bfe5f9da1bd8bcd"
        }
      },
      "name": "ESI Sentence Worth Reviewer",
      "reviewAspect": "checkworthiness",
      "softwareRequirements": [
        "python",
        "pytorch",
        "transformers",
        "RoBERTaModel",
        "RoBERTaTokenizer"
      ],
      "softwareVersion": "0.1.0"
    },
    "timings": {
      "@context": "http://coinform.eu",
      "@type": "Timing",
      "phase": "predict_worthiness",
      "sub_timings": [],
      "total_ms": 2016
    }
  },
  "worthiness_checked_sentences": {
    "predicted_labels": [
      "CFS",
      "CFS",
      "CFS",
      "CFS",
      "CFS",
      "NCS",
      "NCS"
    ],
    "prediction_confidences": [
      1.0,
      1.0,
      1.0,
      1.0,
      1.0,
      1.0,
      1.0
    ],
    "sentence_ids": [
      "zVny6fEGxhaK1HdE3H-3YA",
      "afdz8aeDNEHtFV-Jrr5C_g",
      "4r8tPDjym0ECsuT75ZZkNQ",
      "KijPfGDu450JaUFgBUHttQ",
      "JsWSYRs42wuLzKTxYc82qA",
      "s0MUWAbvsZGICtdZ0h1-Dw",
      "rdWPgez81b6RKT0G6eYqJg"
    ],
    "sentences": [
      "A typical family of four making $75,000 will see their tax bill reduced by $2,000, slashing their tax bill in half.",
      "the coronavirus is a bioweapon",
      "We eliminated an especially cruel tax that fell mostly on Americans making less than $50,000 a year, forcing them to pay tremendous penalties simply because they couldn’t afford government-ordered health plans.",
      "We slashed the business tax rate from 35 percent all the way down to 21 percent, so American companies can compete and win against anyone else anywhere in the world",
      "Toyota and Mazda are opening up a plant in Alabama — a big one.",
      "I hope you will be fine",
      "Cars are amazing"
    ]
  }
}

```

# About the Transformers model
To generate the check-worthiness predictions we fine-tuned a RoBERTa pre-trained model (RobertaForSequenceCLassification by Hugging Face). We fine-tuned the model using the combination of three distinct datasets ([CBD](https://github.com/idirlab/claimspotter), [Clef'20T1](https://github.com/sshaar/clef2020-factchecking-task1.git) and [Poynter data](https://www.poynter.org/ifcn-covid-19-misinformation/))

We merged datasets with different topics and sentence structures:

|       | CBD               | Clef'20T1       | Poynter               |
|-------|-------------------|-----------------|-----------------------|
| Topic | political debates | covid-19 tweets | covid-19 ClaimReviews |



Inspect the combined dataset:

|     | CBD  | Clef'20T1 | Poynter |
|-----|------|-----------|---------|
| CFS | 2345 |       291 | 4609    |
| NCS | 6333 |       346 | -       |
| TOT | 8678 |       637 | 4609    |

We removed some example of the NCS class and splitted the dataset into Training and Validation:

|      | Training | Validation |
|------|----------|------------|
| CFS  | 5208     | 2036       |
| NCS  | 2274     | 429        |
| TOT  | 7482     | 2465       |

These are the results obtained with the model on the validation set:
```
F1_w: 0.844
Acc: 0.95
```


Finally, we evaluated the model on three different datasets:

|     |Poynter eval | Clef'19 test | CB2020 |
|-----|-------------|--------------|--------|
| CFS | 143         | 136          | 51     |
| NCS | -           | 6944         | 49     |
| TOT | 143         | 7080         | 100    |

|       | Poynter eval | Clef'19 test       | CB2020                |
|-------|--------------|--------------------|-----------------------|
| Topic | covid-19     | political debates  | political debates     |

Evaluation results:

|      | Poynter eval | Clef'19 test | CB2020 |
|------|--------------|--------------|--------|
| F1_w | 1            | 0.85         |  0.95  |


# Use the Worthiness Checker into the acred pipeline

To use the service into the `acred` pipeline set the [`worthiness_review`](http://github.com/rdenaux/acred/blob/check-worthiness-dev/acred.ini#L55) parameter as `True` in the `acred.ini` file, otherwise set the parameter as `False` to ignore it.
