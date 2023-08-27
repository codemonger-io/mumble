# Mumble

![Mumble Brand](./mumble-brand.png)

Mumble is a **serverless** implementation of [ActivityPub](https://www.w3.org/TR/activitypub/) on [AWS](https://aws.amazon.com).

[ActivityPub](https://www.w3.org/TR/activitypub/) is a decentralized social networking protocol which is used by [Mastodon](https://joinmastodon.org).

## Features

Mumble is not fully compliant with [ActivityPub](https://www.w3.org/TR/activitypub/) yet, but you can do the following things:
- Create an account reachable from [Mastodon](https://joinmastodon.org)
- Publish a post with optional attachments
    - Only public posts so far
- Deliver posts to your followers
- Be followed by another [Mastodon](https://joinmastodon.org) user

Mumble also provides a simple [viewer app](./cdk/viewer/README.md) so that any guests can see your profile and public activites.
You can promote your mumble account by [sharing the profile URL on the viewer app](#sharing-your-profile).

More features will come in the future.

### Mumble is Serverless

Since Mumble is implemented with [serverless technologies on AWS](https://aws.amazon.com/serverless/), you do not have to spin up and manage persistent servers.
It will greatly reduce your initial cost, and you can scale up as you gain more traction.
FYI: According to [this article](https://cloudonaut.io/mastodon-on-aws/#:~:text=Costs%20for%20running%20Mastodon%20on%20AWS&text=The%20architecture%27s%20monthly%20charges%20are%20about%20%2460%20per%20month.), hosting a minimal [Mastodon](https://joinmastodon.org) setup on [AWS](https://aws.amazon.com) would cost about $60.

### Mumble is NOT

- A hosted service
    - You have to deploy and host Mumble yourself on your own [AWS](https://aws.amazon.com) account.
      You have full control over your data in return.
- An [ActivityPub](https://www.w3.org/TR/activitypub/) client
    - [MumbleBee](https://github.com/codemonger-io/mumble-bee) is the official client for Mumble.
    - A simple [viewer app](./cdk/viewer/README.md) is included, though.

## Getting started

### Prerequisites

You need an [AWS](https://aws.amazon.com) account where you have full privileges to provision resources.

### Deploying Mumble

To deploy Mumble to your [AWS](https://aws.amazon.com) account, please follow the instructions described in [`cdk/README.md`](./cdk/README.md).

### Configuring Mumble

You have to do a few configurations after you deploy Mumble.
Please refer to [Section "After deployment" in `cdk/README.md`](./cdk/README.md#after-deployment).

### Creating a Mumble account

Once you have deployed and configured Mumble, you can create a Mumble account.
Please refer to [Section "Creating a new Mumble user" in `cdk/README.md`](./cdk/README.md#creating-a-new-mumble-user).

### Publish posts from a Mumble client

[MumbleBee](https://github.com/codemonger-io/mumble-bee) is the official client for Mumble.
Please refer to [MumbleBee's repository](https://github.com/codemonger-io/mumble-bee) for more details.

### Sharing your profile

Your profile is served at `https://${YOUR_MUMBLE_DOMAIN_NAME}/viewer/users/${YOUR_ID}/`.

## Background

I often write down thoughts and findings in short texts (mumblings) while I am working.
For that purpose, I used to use [Microsoft Teams](https://www.microsoft.com/en-us/microsoft-teams/group-chat-software), [Slack](https://slack.com/), [Dicord](https://discord.com), or whatever the workplace provided.
These mumblings turned out useful for my colleagues and me.
Now, as a freelance, I started to want to have my own place to publicly write down these mumblings.
[Twitter](https://twitter.com) could have been a good place, but I felt somehow it was not the right place for me.
During the recent turmoil around [Twitter](https://twitter.com), [Mastodon](https://joinmastodon.org), a decentralized social network, caught my attention, and I was attracted to [ActivityPub](https://www.w3.org/TR/activitypub/) behind [Mastodon](https://joinmastodon.org).
Since hosting [Mastodon](https://joinmastodon.org) required a traditional setup of servers that was not the way I was eager to pursue, I decided to implement a serverless version of [ActivityPub](https://www.w3.org/TR/activitypub/) on [AWS](https://aws.amazon.com).

## Development

### Architecture

The architecture of the Mumble service is described in [`docs/architecture.md`](./docs/architecture.md).

### OpenAPI definition

The OpenAPI definition of the Mumble API is available at [`cdk/openapi/api-production.json`](./cdk/openapi/api-production.json).

Thanks to [Redoc](https://github.com/Redocly/redoc), you can browse the Mumble API documentation at [https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/codemonger-io/mumble/main/cdk/openapi/api-production.json](https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/codemonger-io/mumble/main/cdk/openapi/api-production.json).

## License

[MIT](./LICENSE)

"Mumble Brand" (`mumble-brand.png`) by [codemonger](https://codemonger.io) is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).