# Notice Email Parser

Store inbound SES public notice emails in S3 organized by matched criteria

## Setup

* You'll need Python and Node installed as well as Sentry and AWS accounts
* Run `pipenv sync` and `npm install` to install dependencies
* Configure [email receiving in AWS SES](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/receiving-email.html)
* Set up variables in `serverless.yml` in SSM
* Run `npx serverless deploy` to create the resources and deploy the application
