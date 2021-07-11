# EdgeAware

EdgeAware is a virtual edge-network service that permits peer-to-peer data transfer between individual nodes and employs a sophisticated decision-making algorithm to determine if data in the cloud should be available at the edge.

### About the Project

![diagram](assets/diagram.png)

A user having a storage bucket in a certain region can connect to the service to send and receive data. Using a machine-learning algorithm, the priority of the data is predicted and then transmitted asynchronously to the edge of other users in different locations so that it is easily available to them.

Data is categorised according to priority as follows:

- **High**: Data will be available in the sender's bucket, the receiver's bucket, and the receiver's local computer.
- **Medium** : Data will be available in both the sender's and receiver's buckets.
- **Low**: Data will only be available in the sender's bucket.

## Commands

- `register` - Register a user and configure account information
- `login <username> <password>` - Sign in to use the service
- `reset_password <email>` - Get the password reset link
- `send <to_username> <filepath> [<priority>]` - Send a file to a user with optional priority
- `check` - Check tracked files
- `sync [<file_id>]` - Sync all files, or a specific file
- `delete <file_id>` - Delete a file
- `logout` - Logout and stop the service

Utility commands such as `record` and `playback` can be use to store and run commands from a file.

## Technologies used

- [Amazon S3](https://aws.amazon.com/s3/) - Cloud storage service
- [Firebase](https://firebase.google.com/) - User authentication and file commits
- [Boto3](https://boto3.readthedocs.io) - Low-level API to access to AWS services
- [Scikit-learn](https://scikit-learn.org/) - Machine learning algorithm
- [Heroku](https://www.heroku.com/) - Cloud platform to deploy service worker

## Local setup

- Clone this repository

```
git clone https://github.com/aravrs/EdgeAware.git
cd EdgeAware
```

- Install requirements

```
pip install -r requirements.txt
```

- Setup credentials

  - Add firebase app config credentials to [`config.json`](config.json) file.
  - Setup up and run the service worker file, [`worker/tansfer.py`](worker/transfer.py) on any cloud platform (we used [heroku](https://www.heroku.com)) or run it locally.

- Start the EdgeAware CLI

```
python cli.py
```
