# Browser Error Collection Notifications

This is a prototype service that reads processed events from Sentry (exported via Amazon SQS) and evaluates several rules to determine if it should send email alerts.

## Development Setup

Prerequisites:

- Docker 18.03.0
- docker-compose 1.21.0

1. Clone the repository:

   ```sh
   git clone https://github.com/mozilla/bec-alerts.git
   cd bec-alerts
   ```
2. Build the Docker image:

   ```sh
   docker-compose build
   ```
3. Initialize Sentry and create an admin account (requires user input):

   ```sh
   docker-compose run sentry sentry upgrade
   ```
4. Initialize processor database:

   ```sh
   docker-compose run processor bec-alerts manage migrate
   ```
5. Start up services:

   ```sh
   docker-compose up
   ```
6. Visit http://localhost:9000 and finish Sentry setup via the web interface:

   - Use `http://localhost:9000` as the base URL of the install.
   - Create a new project. It's easiest to select "Python" as the project type.
   - Once you see the "Getting Started" page that includes a code sample of sending an error via Python, copy the DSN (which looks like `http://really_long_hash@localhost:9000/2`) to a `.env` file at the root of your repo that should look like this:

     ```
     SENTRY_DSN=http://really_long_hash@sentry:9000/2
     ```

   __Important:__ You must change the `localhost` in the DSN to `sentry`, since it will be used in a Docker container where Sentry is not running on localhost.

### Simulating an Error

If you've set `SENTRY_DSN` in your `.env` file properly, you can simulate sending an error to your running Sentry instance with the `simulate_error` command:

```sh
docker-compose run processor bec-alerts simulate_error
```

## Deployment

The service consists of a few AWS services and a Docker image that is intended to be run on EC2. The required AWS resources are:

- An SQS queue (named `sentry_errors` by default) that Sentry can write to and the app can read from. The app will create the queue on startup itself.
- An SES account for sending email notifications
- An RDS resource running a Postgres database for storing aggregation data

The Docker image defined in `Dockerfile` is used to run two separate processes:

### Processor

Command: `bec-alerts processor`

Reads from SQS to fetch incoming events from Sentry, processes them, and saves the resulting data to Postgres.

The following environment variables are available:

| Name | Required? | Default | Description |
| ---- | --------- | ------- | ----------- |
| `PROCESSOR_SLEEP_DELAY` | :x: | `20` | Seconds to wait between polling the queue |
| `SQS_QUEUE_NAME` | :x: | `sentry_errors` | Name of the queue to poll for events. |
| `AWS_ACCESS_KEY_ID` | :white_check_mark: | | Access Key ID for connecting to AWS |
| `AWS_SECRET_ACCESS_KEY` | :white_check_mark: | | Secret Access Key for connecting to AWS |
| `AWS_DEFAULT_REGION` | :white_check_mark: | | Region for connecting to AWS |
| `SQS_ENDPOINT_URL` | :x: | | Endpoint URL for connection to AWS. Only required for local development. |
| `AWS_CONNECT_TIMEOUT` | :x: | `30` | Timeout for connecting to AWS |
| `AWS_READ_TIMEOUT` | :x: | `30` | Timeout for reading a response from AWS |

### Watcher

Command: `bec-alerts watcher`

Periodically checks for events that have been processed since the last run, and evaluates alert triggers to determine if we should send a notification to users. This process implements its own sleep timer.

The following environment variables are available:

| Name | Required? | Default | Description |
| ---- | --------- | ------- | ----------- |
| `SES_VERIFY_EMAIL` | :x: | `False` | If True, the watcher will attempt to verify the `SES_VERIFY_EMAIL` via API on startup. Should probably be False in production. |
| `WATCHER_SLEEP_DELAY` | :x: | `300` | Seconds to wait between checking for new events and alert triggers |
| `SES_FROM_EMAIL` | :white_check_mark: | `notifications@sentry.prod.mozaws.net` | Email to use in the From field for notifications |
| `AWS_ACCESS_KEY_ID` | :white_check_mark: | | Access Key ID for connecting to AWS |
| `AWS_SECRET_ACCESS_KEY` | :white_check_mark: | | Secret Access Key for connecting to AWS |
| `AWS_DEFAULT_REGION` | :white_check_mark: | | Region for connecting to AWS |
| `SES_ENDPOINT_URL` | :x: | | Endpoint URL for connection to AWS. Only required for local development. |
| `AWS_CONNECT_TIMEOUT` | :x: | `30` | Timeout for connecting to AWS |
| `AWS_READ_TIMEOUT` | :x: | `30` | Timeout for reading a response from AWS |

## License

Browser Error Collection Notifications is licensed under the MPL 2.0. See the `LICENSE` file for details.

The file `sentry/sqs_plugin.py` is a fork of an official Sentry plugin provided by Sentry. It is covered under the Apache License, version 2.0. See the file's comments for details.
