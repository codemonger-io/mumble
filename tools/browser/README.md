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

Some common code resides in [`libactivitypub`](../../lib/libactivitypub) library.

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

will output something similar to the following:
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
python browser.py pull-activities gargron@mastodon.social --num-activities 1
```

will show something similar to the following:
```json
{
  "activities": [
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
    }
  ],
  "referenced": [
    {
      "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
        {
          "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
          "toot": "http://joinmastodon.org/ns#",
          "featured": {
            "@id": "toot:featured",
            "@type": "@id"
          },
          "featuredTags": {
            "@id": "toot:featuredTags",
            "@type": "@id"
          },
          "alsoKnownAs": {
            "@id": "as:alsoKnownAs",
            "@type": "@id"
          },
          "movedTo": {
            "@id": "as:movedTo",
            "@type": "@id"
          },
          "schema": "http://schema.org#",
          "PropertyValue": "schema:PropertyValue",
          "value": "schema:value",
          "discoverable": "toot:discoverable",
          "Device": "toot:Device",
          "Ed25519Signature": "toot:Ed25519Signature",
          "Ed25519Key": "toot:Ed25519Key",
          "Curve25519Key": "toot:Curve25519Key",
          "EncryptedMessage": "toot:EncryptedMessage",
          "publicKeyBase64": "toot:publicKeyBase64",
          "deviceId": "toot:deviceId",
          "claim": {
            "@type": "@id",
            "@id": "toot:claim"
          },
          "fingerprintKey": {
            "@type": "@id",
            "@id": "toot:fingerprintKey"
          },
          "identityKey": {
            "@type": "@id",
            "@id": "toot:identityKey"
          },
          "devices": {
            "@type": "@id",
            "@id": "toot:devices"
          },
          "messageFranking": "toot:messageFranking",
          "messageType": "toot:messageType",
          "cipherText": "toot:cipherText",
          "suspended": "toot:suspended",
          "focalPoint": {
            "@container": "@list",
            "@id": "toot:focalPoint"
          }
        }
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
    },
    {
      "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
        {
          "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
          "toot": "http://joinmastodon.org/ns#",
          "featured": {
            "@id": "toot:featured",
            "@type": "@id"
          },
          "featuredTags": {
            "@id": "toot:featuredTags",
            "@type": "@id"
          },
          "alsoKnownAs": {
            "@id": "as:alsoKnownAs",
            "@type": "@id"
          },
          "movedTo": {
            "@id": "as:movedTo",
            "@type": "@id"
          },
          "schema": "http://schema.org#",
          "PropertyValue": "schema:PropertyValue",
          "value": "schema:value",
          "discoverable": "toot:discoverable",
          "Device": "toot:Device",
          "Ed25519Signature": "toot:Ed25519Signature",
          "Ed25519Key": "toot:Ed25519Key",
          "Curve25519Key": "toot:Curve25519Key",
          "EncryptedMessage": "toot:EncryptedMessage",
          "publicKeyBase64": "toot:publicKeyBase64",
          "deviceId": "toot:deviceId",
          "claim": {
            "@type": "@id",
            "@id": "toot:claim"
          },
          "fingerprintKey": {
            "@type": "@id",
            "@id": "toot:fingerprintKey"
          },
          "identityKey": {
            "@type": "@id",
            "@id": "toot:identityKey"
          },
          "devices": {
            "@type": "@id",
            "@id": "toot:devices"
          },
          "messageFranking": "toot:messageFranking",
          "messageType": "toot:messageType",
          "cipherText": "toot:cipherText",
          "suspended": "toot:suspended",
          "Hashtag": "as:Hashtag",
          "focalPoint": {
            "@container": "@list",
            "@id": "toot:focalPoint"
          }
        }
      ],
      "id": "https://newsie.social/users/dwl",
      "type": "Person",
      "following": "https://newsie.social/users/dwl/following",
      "followers": "https://newsie.social/users/dwl/followers",
      "inbox": "https://newsie.social/users/dwl/inbox",
      "outbox": "https://newsie.social/users/dwl/outbox",
      "featured": "https://newsie.social/users/dwl/collections/featured",
      "featuredTags": "https://newsie.social/users/dwl/collections/tags",
      "preferredUsername": "dwl",
      "name": "Daniel W. Lathrop",
      "summary": "<p>Investigative Journalist. Data Nerd. <span class=\"h-card\"><a href=\"https://newsie.social/@scrippsnews\" class=\"u-url mention\">@<span>scrippsnews</span></a></span> DC Bureau reporter living in Iowa. <a href=\"https://newsie.social/tags/leaktome\" class=\"mention hashtag\" rel=\"tag\">#<span>leaktome</span></a>  <a href=\"https://newsie.social/tags/GirlDad\" class=\"mention hashtag\" rel=\"tag\">#<span>GirlDad</span></a> Signal/Telegram/etc. at 319-244-8873</p><p><a href=\"https://newsie.social/tags/fedi22\" class=\"mention hashtag\" rel=\"tag\">#<span>fedi22</span></a> <a href=\"https://newsie.social/tags/journalism\" class=\"mention hashtag\" rel=\"tag\">#<span>journalism</span></a> <a href=\"https://newsie.social/tags/ddj\" class=\"mention hashtag\" rel=\"tag\">#<span>ddj</span></a> <a href=\"https://newsie.social/tags/datajournalism\" class=\"mention hashtag\" rel=\"tag\">#<span>datajournalism</span></a> <a href=\"https://newsie.social/tags/scrippsnews\" class=\"mention hashtag\" rel=\"tag\">#<span>scrippsnews</span></a> <a href=\"https://newsie.social/tags/opengov\" class=\"mention hashtag\" rel=\"tag\">#<span>opengov</span></a> <a href=\"https://newsie.social/tags/journalist\" class=\"mention hashtag\" rel=\"tag\">#<span>journalist</span></a> <a href=\"https://newsie.social/tags/investigativejournalism\" class=\"mention hashtag\" rel=\"tag\">#<span>investigativejournalism</span></a></p>",
      "url": "https://newsie.social/@dwl",
      "manuallyApprovesFollowers": false,
      "discoverable": true,
      "published": "2023-01-05T00:00:00Z",
      "devices": "https://newsie.social/users/dwl/collections/devices",
      "publicKey": {
        "id": "https://newsie.social/users/dwl#main-key",
        "owner": "https://newsie.social/users/dwl",
        "publicKeyPem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwoyJrw/10a4CYsnkkRJg\nfDHdNEHckJqQVWBxWnU8LXrYYxLsfmbmKeldvorT84Pbg1Rzu5/lbjBKJwo/diG+\nhHrfkkGGeLWsF+dYqf13u1qAvM1vzn+fKlrRdMG6XrcuZaXEO8TkzR6tqcXsTt3U\nKr6w6gAKeoPr6C54C+60mnZBDgMe+49ZbDzF2jHzGESSWe9VtLLAvZI2/tkV+MU/\ncuwPwzuy4MGOGBYqnQb5RyGqseVRFmqIegKNCeSKAFbn9iEatz/WolR4kB+o9/XG\nVZ1ocalVrN7a4SMNFz8jzGcxFdjficUx9TzwjmaD34O3ZiquENUtvk7tW7En14n2\nWwIDAQAB\n-----END PUBLIC KEY-----\n"
      },
      "tag": [
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/Journalism",
          "name": "#Journalism"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/fedi22",
          "name": "#fedi22"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/opengov",
          "name": "#opengov"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/journalist",
          "name": "#journalist"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/ddj",
          "name": "#ddj"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/datajournalism",
          "name": "#datajournalism"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/GirlDad",
          "name": "#GirlDad"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/investigativejournalism",
          "name": "#investigativejournalism"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/scrippsnews",
          "name": "#scrippsnews"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/leaktome",
          "name": "#leaktome"
        }
      ],
      "attachment": [],
      "endpoints": {
        "sharedInbox": "https://newsie.social/inbox"
      },
      "icon": {
        "type": "Image",
        "mediaType": "image/jpeg",
        "url": "https://assets.newsie.social/accounts/avatars/109/638/724/966/446/474/original/0db696a1e22b8823.jpg"
      },
      "image": {
        "type": "Image",
        "mediaType": "image/jpeg",
        "url": "https://assets.newsie.social/accounts/headers/109/638/724/966/446/474/original/81a00be6a325a736.jpeg"
      }
    },
    {
      "@context": [
        "https://www.w3.org/ns/activitystreams",
        {
          "ostatus": "http://ostatus.org#",
          "atomUri": "ostatus:atomUri",
          "inReplyToAtomUri": "ostatus:inReplyToAtomUri",
          "conversation": "ostatus:conversation",
          "sensitive": "as:sensitive",
          "toot": "http://joinmastodon.org/ns#",
          "votersCount": "toot:votersCount",
          "Hashtag": "as:Hashtag"
        }
      ],
      "id": "https://newsie.social/users/dwl/statuses/110186366606387034",
      "type": "Note",
      "summary": null,
      "inReplyTo": null,
      "published": "2023-04-12T14:42:05Z",
      "url": "https://newsie.social/@dwl/110186366606387034",
      "attributedTo": "https://newsie.social/users/dwl",
      "to": [
        "https://www.w3.org/ns/activitystreams#Public"
      ],
      "cc": [
        "https://newsie.social/users/dwl/followers"
      ],
      "sensitive": false,
      "atomUri": "https://newsie.social/users/dwl/statuses/110186366606387034",
      "inReplyToAtomUri": null,
      "conversation": "tag:newsie.social,2023-04-12:objectId=32926056:objectType=Conversation",
      "content": "<p>Hot Take: Other news organizations should strongly consider whether NPR&#39;s exit from <a href=\"https://newsie.social/tags/birdsite\" class=\"mention hashtag\" rel=\"tag\">#<span>birdsite</span></a> and the behavior leading up to it means that only public spirited, journalistic response is to suspend operations as well. <a href=\"https://www.npr.org/2023/04/12/1169269161/npr-leaves-twitter-government-funded-media-label\" target=\"_blank\" rel=\"nofollow noopener noreferrer\"><span class=\"invisible\">https://www.</span><span class=\"ellipsis\">npr.org/2023/04/12/1169269161/</span><span class=\"invisible\">npr-leaves-twitter-government-funded-media-label</span></a> <a href=\"https://newsie.social/tags/Solidarity\" class=\"mention hashtag\" rel=\"tag\">#<span>Solidarity</span></a> <a href=\"https://newsie.social/tags/Journalism\" class=\"mention hashtag\" rel=\"tag\">#<span>Journalism</span></a></p>",
      "contentMap": {
        "en": "<p>Hot Take: Other news organizations should strongly consider whether NPR&#39;s exit from <a href=\"https://newsie.social/tags/birdsite\" class=\"mention hashtag\" rel=\"tag\">#<span>birdsite</span></a> and the behavior leading up to it means that only public spirited, journalistic response is to suspend operations as well. <a href=\"https://www.npr.org/2023/04/12/1169269161/npr-leaves-twitter-government-funded-media-label\" target=\"_blank\" rel=\"nofollow noopener noreferrer\"><span class=\"invisible\">https://www.</span><span class=\"ellipsis\">npr.org/2023/04/12/1169269161/</span><span class=\"invisible\">npr-leaves-twitter-government-funded-media-label</span></a> <a href=\"https://newsie.social/tags/Solidarity\" class=\"mention hashtag\" rel=\"tag\">#<span>Solidarity</span></a> <a href=\"https://newsie.social/tags/Journalism\" class=\"mention hashtag\" rel=\"tag\">#<span>Journalism</span></a></p>"
      },
      "attachment": [],
      "tag": [
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/birdsite",
          "name": "#birdsite"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/Solidarity",
          "name": "#Solidarity"
        },
        {
          "type": "Hashtag",
          "href": "https://newsie.social/tags/Journalism",
          "name": "#Journalism"
        }
      ],
      "replies": {
        "id": "https://newsie.social/users/dwl/statuses/110186366606387034/replies",
        "type": "Collection",
        "first": {
          "type": "CollectionPage",
          "next": "https://newsie.social/users/dwl/statuses/110186366606387034/replies?only_other_accounts=true&page=true",
          "partOf": "https://newsie.social/users/dwl/statuses/110186366606387034/replies",
          "items": []
        }
      }
    }
  ]
}
```