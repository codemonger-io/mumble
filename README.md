# Mumble

![Mumble Brand](./mumble-brand.png)

Mumble is a **serverless** implementation of [Activity Pub](https://www.w3.org/TR/activitypub/) on [AWS](https://aws.amazon.com).

[Activity Pub](https://www.w3.org/TR/activitypub/) is a decentralized social networking protocol which is used by [Mastodon](https://joinmastodon.org).

## Features

Mumble is not fully compliant with [Activity Pub](https://www.w3.org/TR/activitypub/) yet, but you can do the following things:
- Create an account reachable from [Mastodon](https://joinmastodon.org)
- Publish a post with optional attachments
    - Only public posts so far
- Deliver posts to your followers
- Be followed by another [Mastodon](https://joinmastodon.org) user

More features will come in the future.

### Mumble is Serverless

Since Mumble is implemented with [serverless technologies on AWS](https://aws.amazon.com/serverless/), you do not have to spin up and manage persistent servers.
It will greatly reduce your initial cost, and you can scale up as you gain more traction.
FYI: According to [this article](https://cloudonaut.io/mastodon-on-aws/#:~:text=Costs%20for%20running%20Mastodon%20on%20AWS&text=The%20architecture%27s%20monthly%20charges%20are%20about%20%2460%20per%20month.), running [Mastodon](https://joinmastodon.org) on [AWS](https://aws.amazon.com) would cost about $60.

### Mumble is not

- A hosted service
    - You have to deploy and host Mumble yourself on your own [AWS](https://aws.amazon.com) account.
- An [Activity Pub](https://www.w3.org/TR/activitypub/) client
    - [MumbleBee](https://github.com/codemonger-io/mumble-bee) is the official client for Mumble.

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

## License

[MIT](./LICENSE)

"Mumble Brand" (`mumble-brand.png`) by [codemonger](https://codemonger.io) is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).