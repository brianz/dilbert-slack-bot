# dilbert-slack-bot

This is a Dilbert comic Slackbot which will respond with Dilbert commits in a slack channel. This
is used as an example on how to spin up a public API using AWS API Gateway and Lambda with the
[Serverless](https://serverless.com) framework.

Once set up , the commands you can invoke are:

    /dilbert -> today's comic
    /dilbert yesterday -> yesterday's comic
    /dilbert random -> random comic
    /dilbert five days ago -> comic from five days ago
    /dilbert 5 days ago -> comic from five days ago
    /dilbert 12-01-2016 -> comic from Dec. 1, 2016
    /dilbert 2016-12-01 -> comic from Dec. 1, 2016

## Instructions for building

There is an include `Makefile` and `Dockerfile` which will build a `docker` image containing
everything needed to deploy the API endpoint using Serverless.

### Setup .env

Create a `.env` file in the root directory which includes the following:

    AWS_SECRET_ACCESS_KEY=your-secret-aws-access-key
    AWS_ACCESS_KEY_ID=your-access-key

### Build Docker image (optional)

    $ make
    $ make shell

You'll now be inside of the docker container which has all of the needed libraries, notably
`serverless`.

If you'd like to use serverless on your local system and skip the Docker step simply follow the
Serverless docs for installation.  This repo assumes Serverless v1.3.

### Deploy 

From within the Docker container (or on your local system):

    root@6c5216631e2f:/code# cd dilbert
    root@6c5216631e2f:/code/dilbert# sls deploy

The output from this will be an API Gateway URL which you can use to setup your [custom Slash
command in Slack](https://api.slack.com/slash-commands).

In addition to the API Gateway endpoint serverless will create:

- lambda function to process the request -> `handler.py`
- DynamoDB table to cache the Dilbert image urls -> see `serverless.yml`
