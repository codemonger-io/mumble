# ActivityPub Browser

Simple Python script to browse on [ActivityPub](https://www.w3.org/TR/activitypub/) networks.

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
  collection       Pulls a collection.
  finger           WebFingers ACCOUNT and prints the ActivityPub actor URI.
  object           Obtains an object.
  pull-activities  Pulls latest activities from a given account.
```

The following commands are "primitive":
- [`finger`](#command-finger)
- [`object`](#command-object)

The following commands are "composite":
- [`collection`](#command-collection)
- [`pull-activities`](#command-pull-activities)

You can also [chain the commands](#chaining-commands).

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

#### Command: object

Obtains the object at a given URI.
`python browser.py object --help` will show messages similar to the following:

```
Usage: browser.py object [OPTIONS] OBJECT

  Obtains an object.

  OBJECT is the object URI to obtain. The object URI is read from the standard
  input if OBJECT is '-'.

Options:
  --query JMESPATH  JMESPath expression to filter the information in the
                    obtained object to be printed. the entire object is
                    printed if omitted.
  --dump DUMP       path to a file where the pulled object is to be saved. no
                    object is saved if omitted.
  --help            Show this message and exit.
```

The following command:
```sh
python browser.py object https://mastodon.social/users/Gargron
```
will output like:
```json
{
  "@context": [
    // ... truncated
  ],
  "id": "https://mastodon.social/users/Gargron",
  "type": "Person",
  "following": "https://mastodon.social/users/Gargron/following",
  "followers": "https://mastodon.social/users/Gargron/followers",
  "inbox": "https://mastodon.social/users/Gargron/inbox",
  "outbox": "https://mastodon.social/users/Gargron/outbox",
  "featured": "https://mastodon.social/users/Gargron/collections/featured",
  "featuredTags": "https://mastodon.social/users/Gargron/collections/tags",
  "preferredUsername": "Gargron",
  "name": "Eugen Rochko",
  "summary": "<p>Founder, CEO and lead developer <span class=\"h-card\"><a href=\"https://mastodon.social/@Mastodon\" class=\"u-url mention\">@<span>Mastodon</span></a></span>, Germany.</p>",
  "url": "https://mastodon.social/@Gargron",
  "manuallyApprovesFollowers": false,
  "discoverable": true,
  "published": "2016-03-16T00:00:00Z",
  "devices": "https://mastodon.social/users/Gargron/collections/devices",
  "alsoKnownAs": [
    "https://tooting.ai/users/Gargron"
  ],
  "publicKey": {
    "id": "https://mastodon.social/users/Gargron#main-key",
    "owner": "https://mastodon.social/users/Gargron",
    "publicKeyPem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvXc4vkECU2/CeuSo1wtn\nFoim94Ne1jBMYxTZ9wm2YTdJq1oiZKif06I2fOqDzY/4q/S9uccrE9Bkajv1dnkO\nVm31QjWlhVpSKynVxEWjVBO5Ienue8gND0xvHIuXf87o61poqjEoepvsQFElA5ym\novljWGSA/jpj7ozygUZhCXtaS2W5AD5tnBQUpcO0lhItYPYTjnmzcc4y2NbJV8hz\n2s2G8qKv8fyimE23gY1XrPJg+cRF+g4PqFXujjlJ7MihD9oqtLGxbu7o1cifTn3x\nBfIdPythWu5b4cujNsB3m3awJjVmx+MHQ9SugkSIYXV0Ina77cTNS0M2PYiH1PFR\nTwIDAQAB\n-----END PUBLIC KEY-----\n"
  },
  "tag": [],
  "attachment": [
    {
      "type": "PropertyValue",
      "name": "Patreon",
      "value": "<a href=\"https://www.patreon.com/mastodon\" target=\"_blank\" rel=\"nofollow noopener noreferrer me\"><span class=\"invisible\">https://www.</span><span class=\"\">patreon.com/mastodon</span><span class=\"invisible\"></span></a>"
    },
    {
      "type": "PropertyValue",
      "name": "GitHub",
      "value": "<a href=\"https://github.com/Gargron\" target=\"_blank\" rel=\"nofollow noopener noreferrer me\"><span class=\"invisible\">https://</span><span class=\"\">github.com/Gargron</span><span class=\"invisible\"></span></a>"
    }
  ],
  "endpoints": {
    "sharedInbox": "https://mastodon.social/inbox"
  },
  "icon": {
    "type": "Image",
    "mediaType": "image/jpeg",
    "url": "https://files.mastodon.social/accounts/avatars/000/000/001/original/dc4286ceb8fab734.jpg"
  },
  "image": {
    "type": "Image",
    "mediaType": "image/jpeg",
    "url": "https://files.mastodon.social/accounts/headers/000/000/001/original/3b91c9965d00888b.jpeg"
  }
}
```

The `--query JMESPATH` option can transform the output with a [JMESPath](https://jmespath.org) expression specified to `JMESPATH`.

Here is an example to output only "outbox" field:
```sh
python browser.py object https://mastodon.social/users/Gargron --query "outbox"
```
that will output:
```
https://mastodon.social/users/Gargron/outbox
```

Another example to output "outbox", "followers", and "following" fields:
```sh
python browser.py object https://mastodon.social/users/Gargron --query "{outbox: outbox, followers: followers, following: following}"
```
that will output:
```json
{
  "outbox": "https://mastodon.social/users/Gargron/outbox",
  "followers": "https://mastodon.social/users/Gargron/followers",
  "following": "https://mastodon.social/users/Gargron/following"
}
```

#### Command: collection

Pulls a page of a given collection object.
Running `python browser.py collection --help` will show messages similar to the following:

```
Usage: browser.py collection [OPTIONS] COLLECTION

  Pulls a collection.

  COLLECTION is the collection URI to be pulled. The collection URI is read
  from the standard input if COLLECTION is '-'.

Options:
  --page PAGE       page in the collection to pull. starts from 1 (default).
  --query JMESPATH  JMESPath expression that filters the information in pulled
                    items to be printed. all the items are printed if omitted.
  --dump DUMP       path to a file where pulled items are to be saved. nothing
                    is saved if omitted.
  --help            Show this message and exit.
```

The following command:
```sh
python browser.py collection https://mastodon.social/users/Gargron/outbox
```
will output like:
```json
[
  {
    "id": "https://mastodon.social/users/Gargron/statuses/110188752496442723/activity",
    "type": "Create",
    "actor": "https://mastodon.social/users/Gargron",
    "published": "2023-04-13T00:48:51Z",
    "to": [
      "https://www.w3.org/ns/activitystreams#Public"
    ],
    "cc": [
      "https://mastodon.social/users/Gargron/followers",
      "https://infosec.exchange/users/micahflee",
      "https://ohai.social/users/deskJet95",
      "https://dmv.community/users/jcrabapple"
    ],
    "object": {
      "id": "https://mastodon.social/users/Gargron/statuses/110188752496442723",
      "type": "Note",
      "summary": null,
      "inReplyTo": "https://infosec.exchange/users/micahflee/statuses/110188748259282169",
      "published": "2023-04-13T00:48:51Z",
      "url": "https://mastodon.social/@Gargron/110188752496442723",
      "attributedTo": "https://mastodon.social/users/Gargron",
      "to": [
        "https://www.w3.org/ns/activitystreams#Public"
      ],
      "cc": [
        "https://mastodon.social/users/Gargron/followers",
        "https://infosec.exchange/users/micahflee",
        "https://ohai.social/users/deskJet95",
        "https://dmv.community/users/jcrabapple"
      ],
      "sensitive": false,
      "atomUri": "https://mastodon.social/users/Gargron/statuses/110188752496442723",
      "inReplyToAtomUri": "https://infosec.exchange/users/micahflee/statuses/110188748259282169",
      "conversation": "tag:infosec.exchange,2023-04-13:objectId=57639509:objectType=Conversation",
      "content": "<p><span class=\"h-card\"><a href=\"https://infosec.exchange/@micahflee\" class=\"u-url mention\">@<span>micahflee</span></a></span> <span class=\"h-card\"><a href=\"https://ohai.social/@deskJet95\" class=\"u-url mention\">@<span>deskJet95</span></a></span> <span class=\"h-card\"><a href=\"https://dmv.community/@jcrabapple\" class=\"u-url mention\">@<span>jcrabapple</span></a></span> I&#39;m sorry, I&#39;m not seeing any difference to any given Mastodon app</p>",
      "contentMap": {
        "en": "<p><span class=\"h-card\"><a href=\"https://infosec.exchange/@micahflee\" class=\"u-url mention\">@<span>micahflee</span></a></span> <span class=\"h-card\"><a href=\"https://ohai.social/@deskJet95\" class=\"u-url mention\">@<span>deskJet95</span></a></span> <span class=\"h-card\"><a href=\"https://dmv.community/@jcrabapple\" class=\"u-url mention\">@<span>jcrabapple</span></a></span> I&#39;m sorry, I&#39;m not seeing any difference to any given Mastodon app</p>"
      },
      "attachment": [],
      "tag": [
        {
          "type": "Mention",
          "href": "https://infosec.exchange/users/micahflee",
          "name": "@micahflee@infosec.exchange"
        },
        {
          "type": "Mention",
          "href": "https://ohai.social/users/deskJet95",
          "name": "@deskJet95@ohai.social"
        },
        {
          "type": "Mention",
          "href": "https://dmv.community/users/jcrabapple",
          "name": "@jcrabapple@dmv.community"
        }
      ],
      "replies": {
        "id": "https://mastodon.social/users/Gargron/statuses/110188752496442723/replies",
        "type": "Collection",
        "first": {
          "type": "CollectionPage",
          "next": "https://mastodon.social/users/Gargron/statuses/110188752496442723/replies?only_other_accounts=true&page=true",
          "partOf": "https://mastodon.social/users/Gargron/statuses/110188752496442723/replies",
          "items": []
        }
      }
    }
  },
  // ... truncated
]
```

The `--query JMESPATH` option can transform the output with a [JMESPath](https://jmespath.org) expression specified to `JMESPATH`.

Here is an example to output only "content" of the object in "Create" activities:
```sh
python browser.py collection https://mastodon.social/users/Gargron/outbox --query "[?type=='Create'].object.content"
```
that will output like:
```json
[
  "<p><span class=\"h-card\"><a href=\"https://infosec.exchange/@micahflee\" class=\"u-url mention\">@<span>micahflee</span></a></span> <span class=\"h-card\"><a href=\"https://ohai.social/@deskJet95\" class=\"u-url mention\">@<span>deskJet95</span></a></span> <span class=\"h-card\"><a href=\"https://dmv.community/@jcrabapple\" class=\"u-url mention\">@<span>jcrabapple</span></a></span> I&#39;m sorry, I&#39;m not seeing any difference to any given Mastodon app</p>",
  "<p><span class=\"h-card\"><a href=\"https://infosec.exchange/@micahflee\" class=\"u-url mention\">@<span>micahflee</span></a></span> <span class=\"h-card\"><a href=\"https://ohai.social/@deskJet95\" class=\"u-url mention\">@<span>deskJet95</span></a></span> <span class=\"h-card\"><a href=\"https://dmv.community/@jcrabapple\" class=\"u-url mention\">@<span>jcrabapple</span></a></span> What does this screenshot show?</p>",
  "<p><span class=\"h-card\"><a href=\"https://infosec.exchange/@micahflee\" class=\"u-url mention\">@<span>micahflee</span></a></span> Much better UX in what ways?</p>",
  "<p><span class=\"h-card\"><a href=\"https://cosocial.ca/@boris\" class=\"u-url mention\">@<span>boris</span></a></span> <span class=\"h-card\"><a href=\"https://pixel.kitchen/@jenn\" class=\"u-url mention\">@<span>jenn</span></a></span> <span class=\"h-card\"><a href=\"https://fosstodon.org/@haubles\" class=\"u-url mention\">@<span>haubles</span></a></span> <span class=\"h-card\"><a href=\"https://hachyderm.io/@simonwistow\" class=\"u-url mention\">@<span>simonwistow</span></a></span> <span class=\"h-card\"><a href=\"https://me.dm/@anildash\" class=\"u-url mention\">@<span>anildash</span></a></span> We&#39;re working on open-sourcing our Terraform config for Mastodon behind Fastly.</p>",
  "<p><span class=\"h-card\"><a href=\"https://mastodon.social/@Walwal\" class=\"u-url mention\">@<span>Walwal</span></a></span> Thank you.</p>",
  "<p><span class=\"h-card\"><a href=\"https://mastodon.social/@Walwal\" class=\"u-url mention\">@<span>Walwal</span></a></span> Is there no way to report something on Bluesky?</p>",
  "<p><span class=\"h-card\"><a href=\"https://mastodon.social/@Walwal\" class=\"u-url mention\">@<span>Walwal</span></a></span> No</p>",
  "<p><span class=\"h-card\"><a href=\"https://mastodon.social/@abcxyz\" class=\"u-url mention\">@<span>abcxyz</span></a></span> It&#39;s in progress, planned for release 4.2, but I don&#39;t have an exact ETA for you.</p>"
]
```

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
    // ... truncated
  ]
}
```

The `--filter FILTER` option accepts a [JMESPath](https://jmespath.org) expression as `FILTER`.
The command collects activites that is evaluated as non-null by `FILTER`.
Here is an example to pull only "Create" activities:

```sh
python browser.py pull-activities gargron@mastodon.social --filter "type == 'Create' && @ || null"
```

Please note that `FILTER` does not transform the output.

#### Chaining commands

You can chain the commands with pipes (`|`).

The following example:
```sh
python browser.py finger gargron@mastodon.social \
    | python browser.py object - --query "outbox" \
    | python browser.py collection - --query "[?type=='Create'].object.content"
```
will output like:
```json
[
  "<p><span class=\"h-card\"><a href=\"https://infosec.exchange/@micahflee\" class=\"u-url mention\">@<span>micahflee</span></a></span> <span class=\"h-card\"><a href=\"https://ohai.social/@deskJet95\" class=\"u-url mention\">@<span>deskJet95</span></a></span> <span class=\"h-card\"><a href=\"https://dmv.community/@jcrabapple\" class=\"u-url mention\">@<span>jcrabapple</span></a></span> I&#39;m sorry, I&#39;m not seeing any difference to any given Mastodon app</p>",
  "<p><span class=\"h-card\"><a href=\"https://infosec.exchange/@micahflee\" class=\"u-url mention\">@<span>micahflee</span></a></span> <span class=\"h-card\"><a href=\"https://ohai.social/@deskJet95\" class=\"u-url mention\">@<span>deskJet95</span></a></span> <span class=\"h-card\"><a href=\"https://dmv.community/@jcrabapple\" class=\"u-url mention\">@<span>jcrabapple</span></a></span> What does this screenshot show?</p>",
  "<p><span class=\"h-card\"><a href=\"https://infosec.exchange/@micahflee\" class=\"u-url mention\">@<span>micahflee</span></a></span> Much better UX in what ways?</p>",
  "<p><span class=\"h-card\"><a href=\"https://cosocial.ca/@boris\" class=\"u-url mention\">@<span>boris</span></a></span> <span class=\"h-card\"><a href=\"https://pixel.kitchen/@jenn\" class=\"u-url mention\">@<span>jenn</span></a></span> <span class=\"h-card\"><a href=\"https://fosstodon.org/@haubles\" class=\"u-url mention\">@<span>haubles</span></a></span> <span class=\"h-card\"><a href=\"https://hachyderm.io/@simonwistow\" class=\"u-url mention\">@<span>simonwistow</span></a></span> <span class=\"h-card\"><a href=\"https://me.dm/@anildash\" class=\"u-url mention\">@<span>anildash</span></a></span> We&#39;re working on open-sourcing our Terraform config for Mastodon behind Fastly.</p>",
  "<p><span class=\"h-card\"><a href=\"https://mastodon.social/@Walwal\" class=\"u-url mention\">@<span>Walwal</span></a></span> Thank you.</p>",
  "<p><span class=\"h-card\"><a href=\"https://mastodon.social/@Walwal\" class=\"u-url mention\">@<span>Walwal</span></a></span> Is there no way to report something on Bluesky?</p>",
  "<p><span class=\"h-card\"><a href=\"https://mastodon.social/@Walwal\" class=\"u-url mention\">@<span>Walwal</span></a></span> No</p>",
  "<p><span class=\"h-card\"><a href=\"https://mastodon.social/@abcxyz\" class=\"u-url mention\">@<span>abcxyz</span></a></span> It&#39;s in progress, planned for release 4.2, but I don&#39;t have an exact ETA for you.</p>"
]
```