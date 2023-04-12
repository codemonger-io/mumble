# ActivityPub Browser

Simple Python script to browse on ActivityPub networks.

## Getting started

### Installing Python

You need Python 3.8 or later installed.

### Resolving dependencies

I recommend you using a virtual environment to avoid messing up your machine.
This project supposes your virtual environment is configured in `venv` folder.

```sh
python -m venv ./venv
. ./venv/bin/activate
```

Necessary packages are listed in [`requirements.txt`](./requirements.txt).

```sh
pip install -r requirements.txt
```

Some common code resides in [`libactivitypub`](../../lib/libactivitypub) local package.

```sh
pip install ../../lib/libactivitypub
```

### Running browser.py

Running `python browser.py --help` will show messages similar to the following:

```
Usage: browser.py [OPTIONS] COMMAND [ARGS]...

  Simple browser for ActivityPub networks.

Options:
  --debug  turns on debug messages
  --help   Show this message and exit.

Commands:
  actor            Obtains an actor.
  collection       Pulls a collection.
  finger           WebFingers ACCOUNT and prints the ActivityPub actor URI.
  object           Obtains an object.
  pull-activities  Pulls latest activities from a given account.
```

#### Command: finger

Resolves the actor URI of a given account via [WebFinger](https://webfinger.net).

The following command:
```sh
python browser.py finger gargron@mastodon.social
```
will output:
```
https://mastodon.social/users/Gargron
```

#### Command: actor

#### Command: collection

#### Command: object

#### Command: pull-activities

Pulls activities of a given account.

Running `python browser.py pull-activities --help` will show messages similar to the following:
```
Usage: browser.py pull-activities [OPTIONS] ACCOUNT

  Pulls latest activities from a given account.

  ACCOUNT must be a WebFinger ID; e.g., "gargron@mastodon.social".

Options:
  --num-activities NACTS  number of activities to pull. this number counts
                          activities after FILTER is applied. 20 by default.
  --filter FILTER         JMESPath expression to filter the pulled activities.
                          this expression is applied to each activity, and an
                          activity is collected if this expression results in
                          a non-null value (results are discarded). all the
                          activities are collected if omitted.
  --help                  Show this message and exit.
```

The following command:
```sh
python browser.py pull-activities gargron@mastodon.social --num-activities 3
```
will show something similar to the following (you can find the full output in [`sample-activities.json`](./sample-activities.json)):
```json
{
  "activities": [
    {
      "id": "https://mastodon.social/users/Gargron/statuses/110186684417144088/activity",
      "type": "Create",
      "actor": "https://mastodon.social/users/Gargron",
      "published": "2023-04-12T16:02:55Z",
      "to": [
        "https://www.w3.org/ns/activitystreams#Public"
      ],
      "cc": [
        "https://mastodon.social/users/Gargron/followers",
        "https://cosocial.ca/users/boris",
        "https://pixel.kitchen/users/jenn",
        "https://fosstodon.org/users/haubles",
        "https://hachyderm.io/users/simonwistow",
        "https://me.dm/users/anildash"
      ],
      "object": {
        "id": "https://mastodon.social/users/Gargron/statuses/110186684417144088",
        "type": "Note",
        "summary": null,
        "inReplyTo": "https://cosocial.ca/users/boris/statuses/110186624185819449",
        "published": "2023-04-12T16:02:55Z",
        "url": "https://mastodon.social/@Gargron/110186684417144088",
        "attributedTo": "https://mastodon.social/users/Gargron",
        "to": [
          "https://www.w3.org/ns/activitystreams#Public"
        ],
        "cc": [
          "https://mastodon.social/users/Gargron/followers",
          "https://cosocial.ca/users/boris",
          "https://pixel.kitchen/users/jenn",
          "https://fosstodon.org/users/haubles",
          "https://hachyderm.io/users/simonwistow",
          "https://me.dm/users/anildash"
        ],
        "sensitive": false,
        "atomUri": "https://mastodon.social/users/Gargron/statuses/110186684417144088",
        "inReplyToAtomUri": "https://cosocial.ca/users/boris/statuses/110186624185819449",
        "conversation": "tag:cosocial.ca,2023-04-12:objectId=195901:objectType=Conversation",
        "content": "<p><span class=\"h-card\"><a href=\"https://cosocial.ca/@boris\" class=\"u-url mention\">@<span>boris</span></a></span> <span class=\"h-card\"><a href=\"https://pixel.kitchen/@jenn\" class=\"u-url mention\">@<span>jenn</span></a></span> <span class=\"h-card\"><a href=\"https://fosstodon.org/@haubles\" class=\"u-url mention\">@<span>haubles</span></a></span> <span class=\"h-card\"><a href=\"https://hachyderm.io/@simonwistow\" class=\"u-url mention\">@<span>simonwistow</span></a></span> <span class=\"h-card\"><a href=\"https://me.dm/@anildash\" class=\"u-url mention\">@<span>anildash</span></a></span> We&#39;re working on open-sourcing our Terraform config for Mastodon behind Fastly.</p>",
        "contentMap": {
          "en": "<p><span class=\"h-card\"><a href=\"https://cosocial.ca/@boris\" class=\"u-url mention\">@<span>boris</span></a></span> <span class=\"h-card\"><a href=\"https://pixel.kitchen/@jenn\" class=\"u-url mention\">@<span>jenn</span></a></span> <span class=\"h-card\"><a href=\"https://fosstodon.org/@haubles\" class=\"u-url mention\">@<span>haubles</span></a></span> <span class=\"h-card\"><a href=\"https://hachyderm.io/@simonwistow\" class=\"u-url mention\">@<span>simonwistow</span></a></span> <span class=\"h-card\"><a href=\"https://me.dm/@anildash\" class=\"u-url mention\">@<span>anildash</span></a></span> We&#39;re working on open-sourcing our Terraform config for Mastodon behind Fastly.</p>"
        },
        "attachment": [],
        "tag": [
          {
            "type": "Mention",
            "href": "https://cosocial.ca/users/boris",
            "name": "@boris@cosocial.ca"
          },
          {
            "type": "Mention",
            "href": "https://pixel.kitchen/users/jenn",
            "name": "@jenn@pixel.kitchen"
          },
          {
            "type": "Mention",
            "href": "https://fosstodon.org/users/haubles",
            "name": "@haubles@fosstodon.org"
          },
          {
            "type": "Mention",
            "href": "https://hachyderm.io/users/simonwistow",
            "name": "@simonwistow@hachyderm.io"
          },
          {
            "type": "Mention",
            "href": "https://me.dm/users/anildash",
            "name": "@anildash@me.dm"
          }
        ],
        "replies": {
          "id": "https://mastodon.social/users/Gargron/statuses/110186684417144088/replies",
          "type": "Collection",
          "first": {
            "type": "CollectionPage",
            "next": "https://mastodon.social/users/Gargron/statuses/110186684417144088/replies?only_other_accounts=true&page=true",
            "partOf": "https://mastodon.social/users/Gargron/statuses/110186684417144088/replies",
            "items": []
          }
        }
      }
    },
    {
      "id": "https://mastodon.social/users/Gargron/statuses/110186433571789132/activity",
      "type": "Announce",
      "actor": "https://mastodon.social/users/Gargron",
      "published": "2023-04-12T14:59:07Z",
      "to": [
        "https://www.w3.org/ns/activitystreams#Public"
      ],
      "cc": [
        "https://newsie.social/users/dwl",
        "https://mastodon.social/users/Gargron/followers"
      ],
      "object": "https://newsie.social/users/dwl/statuses/110186366606387034"
    },
    {
      "id": "https://mastodon.social/users/Gargron/statuses/110180812505522748/activity",
      "type": "Announce",
      "actor": "https://mastodon.social/users/Gargron",
      "published": "2023-04-11T15:09:36Z",
      "to": [
        "https://www.w3.org/ns/activitystreams#Public"
      ],
      "cc": [
        "https://mastodon.art/users/tinimalitius",
        "https://mastodon.social/users/Gargron/followers"
      ],
      "object": "https://mastodon.art/users/tinimalitius/statuses/110067493683291887"
    }
  ],
  "referenced": [
    {
        // ... truncated
    }
  ]
}
```