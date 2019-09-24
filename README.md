# Serverless Inbound Email Storage

Store inbound SES emails in S3 organized by matched criteria

## Setup

* Install the [Serverless framework](https://serverless.com/framework/docs/) (if not already installed)
* Configure [email receiving in AWS SES](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/receiving-email.html)
* Copy `.env.sample` to `.env`, replacing the sample values with your own
* Run `npm install` to install plugin dependencies
* Run `sls deploy` to create the resources and deploy the application
