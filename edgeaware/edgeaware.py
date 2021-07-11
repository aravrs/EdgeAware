import boto3
import pyrebase
from tabulate import tabulate
from termcolor import colored

import edgeaware.ml as ml


class EdgeAware:
    # TODO: docstrings
    def __init__(self, firebaseConfig):
        self.user = None
        self.user_data = None

        firebase = pyrebase.initialize_app(firebaseConfig)
        self.auth = firebase.auth()
        self.db = firebase.database()

    def register(
        self,
        email,
        username,
        password,
        aws_access_key_id,
        aws_secret_access_key,
        region_name,
        bucket_name,
    ):
        self.user = self.auth.create_user_with_email_and_password(
            email=email, password=password
        )
        self.user_data = {
            "username": username,
            "email": email,
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "region_name": region_name,
            "bucket_name": bucket_name,
        }
        self.db.child("users").child(username).push(
            self.user_data, self.user["idToken"]
        )
        print(colored(f"Registered, {username}!", "green"))

    def login(
        self,
        username,
        password,
    ):
        db_user_data = self.db.child("users").child(username).get().each()[0].val()

        self.user = self.auth.sign_in_with_email_and_password(
            email=db_user_data["email"],
            password=password,
        )

        if self.user["registered"]:
            self.user_data = db_user_data
            print(colored(f"Logged in, {username}!", "green"))

    def reset_password(
        self,
        email,
    ):
        self.auth.send_password_reset_email(email)
        print(colored(f"Password reset mail is sent to {email}.", "blue"))

    def registered(func):
        def check(self, *args, **kwargs):
            if self.user and self.user.get("registered"):
                return func(self, *args, **kwargs)
            else:
                print(colored("Please login!", "red"))

        return check

    @registered
    def send(
        self,
        to_username,
        file_path,
        priority=None,
    ):
        # update meta
        metadata = {
            "sender": self.user_data["username"],
            "receiver": to_username,
            "file_path": file_path,
            "priority": None,
            "inS3_sender": True,
            "inS3_receiver": False,
            "inLocal_sender": False,
            "inLocal_receiver": False,
            "synced": False,
        }
        push_meta = self.db.child("docs").push(metadata)

        # predict priority
        if priority is None:
            priority = ml.predict(metadata)
            print(f"Predicted file priority is {priority}.")

        assert priority.lower() in ["high", "medium", "low"]
        self.db.child("docs").child(push_meta["name"]).update(
            {"priority": priority.lower()}
        )
        print(f"File {file_path} tracked, will be synced to {to_username}!")

        # upload user s3
        boto3.resource(
            service_name="s3",
            region_name=self.user_data["region_name"],
            aws_access_key_id=self.user_data["aws_access_key_id"],
            aws_secret_access_key=self.user_data["aws_secret_access_key"],
        ).Bucket(self.user_data["bucket_name"]).upload_file(
            Filename=file_path, Key=file_path
        )
        print(f"Uploaded to your bucket, {self.user_data['bucket_name']}!")

        # update meta
        self.db.child("docs").child(push_meta["name"]).update({"inS3_sender": True})

    def _get_docs(self, user, sender=False):
        all_docs = self.db.child("docs").get()

        # fetch where user is receiver/sender
        user_docs = []
        if all_docs.each():
            for doc in all_docs.each():
                if doc.val()["receiver"] == user:
                    user_docs.append(doc)
                if sender and doc.val()["sender"] == user:
                    user_docs.append(doc)

        return user_docs

    @registered
    def sync(
        self,
        file_id=None,
    ):
        print(colored("Syncing...", "blue"))
        user_docs = self._get_docs(self.user_data["username"])

        # s3 bucket functions
        for idx, doc in enumerate(user_docs):

            # force download if given file id
            override = False
            if file_id is not None and file_id == str(idx):
                override = True

            if override or not doc.val()["synced"]:
                print(
                    colored(f"[{idx}] ", "magenta") + f"Sender: {doc.val()['sender']}",
                    f"File: {doc.val()['file_path']}",
                    f"Priority: {doc.val()['priority']}",
                    f"Synced: {doc.val()['synced']}",
                    sep=" | ",
                )

                if override or doc.val()["priority"] == "low":
                    # *** do nothing *** #
                    print(f"File available in {doc.val()['sender']} bucket.")

                if override or (
                    doc.val()["priority"] in ["medium", "high"]
                    and doc.val()["inS3_sender"] == True
                ):
                    # *** move from sender s3 to user s3 *** #
                    if doc.val()["inS3_receiver"] == False:
                        print(
                            f"File shall be available in your bucket, {self.user_data['bucket_name']}."
                        )
                    elif doc.val()["inS3_receiver"]:
                        print(
                            f"File available in your bucket, {self.user_data['bucket_name']}."
                        )

                if override or (
                    doc.val()["priority"] == "high"
                    and doc.val()["inLocal_receiver"] != True
                ):
                    # *** download to user's local machine *** #

                    if doc.val()["inS3_receiver"]:
                        boto3.resource(
                            service_name="s3",
                            region_name=self.user_data["region_name"],
                            aws_access_key_id=self.user_data["aws_access_key_id"],
                            aws_secret_access_key=self.user_data[
                                "aws_secret_access_key"
                            ],
                        ).Bucket(self.user_data["bucket_name"]).download_file(
                            Key=doc.val()["file_path"], Filename=doc.val()["file_path"]
                        )

                        # update meta
                        self.db.child("docs").child(doc.key()).update(
                            {"inLocal_receiver": True}
                        )
                        print(f"File available in your local machine.")

                    elif doc.val()["inS3_sender"]:

                        sender_data = (
                            self.db.child("users")
                            .child(doc.val()["sender"])
                            .get()
                            .each()[0]
                            .val()
                        )

                        boto3.resource(
                            service_name="s3",
                            region_name=sender_data["region_name"],
                            aws_access_key_id=sender_data["aws_access_key_id"],
                            aws_secret_access_key=sender_data["aws_secret_access_key"],
                        ).Bucket(sender_data["bucket_name"]).download_file(
                            Key=doc.val()["file_path"], Filename=doc.val()["file_path"]
                        )

                        # update meta
                        self.db.child("docs").child(doc.key()).update(
                            {"inLocal_receiver": True}
                        )
                        print(f"File available in your local machine.")

                    else:
                        print(
                            "File not found in any bucket, please delete tracked meta."
                        )

                self.db.child("docs").child(doc.key()).update({"synced": True})

        print(colored("Sync complete.", "blue"))

    @registered
    def delete(self, file_id):
        print(colored("Deleting...", "blue"))
        user_docs = self._get_docs(self.user_data["username"], sender=True)

        for idx, doc in enumerate(user_docs):
            if file_id == str(idx):
                print(
                    colored(f"[{idx}] ", "magenta") + f"Sender: {doc.val()['sender']}",
                    f"File: {doc.val()['file_path']}",
                    f"Priority: {doc.val()['priority']}",
                    f"Synced: {doc.val()['synced']}",
                    sep=" | ",
                )

                if doc.val()["inS3_sender"]:
                    # delete sender s3
                    sender_data = (
                        self.db.child("users")
                        .child(doc.val()["sender"])
                        .get()
                        .each()[0]
                        .val()
                    )

                    boto3.resource(
                        service_name="s3",
                        region_name=sender_data["region_name"],
                        aws_access_key_id=sender_data["aws_access_key_id"],
                        aws_secret_access_key=sender_data["aws_secret_access_key"],
                    ).Bucket(sender_data["bucket_name"]).delete_objects(
                        Delete={"Objects": [{"Key": doc.val()["file_path"]}]}
                    )
                    print(
                        f"File deleted from {sender_data['username']} bucket, {sender_data['bucket_name']}"
                    )

                if doc.val()["inS3_receiver"]:
                    # delete receiver(user) s3
                    boto3.resource(
                        service_name="s3",
                        region_name=self.user_data["region_name"],
                        aws_access_key_id=self.user_data["aws_access_key_id"],
                        aws_secret_access_key=self.user_data["aws_secret_access_key"],
                    ).Bucket(self.user_data["bucket_name"]).delete_objects(
                        Delete={"Objects": [{"Key": doc.val()["file_path"]}]}
                    )
                    print(
                        f"File deleted from {self.user_data['username']} bucket, {self.user_data['bucket_name']}"
                    )

                # firebase delete meta
                self.db.child("docs").child(doc.key()).remove()

                print("File deleted.")

    @registered
    def check(self):
        user_docs = self._get_docs(self.user_data["username"], sender=True)

        if len(user_docs) < 1:
            print(colored("No files tracked.", "magenta"))

        else:
            headers = [
                colored("ID", "magenta"),
                colored("SENDER", "magenta"),
                colored("RECEIVER", "magenta"),
                colored("FILE", "magenta"),
                colored("PRIORITY", "magenta"),
                colored("SYNCED", "magenta"),
            ]

            # update table
            table = [
                [
                    idx,
                    doc.val()["sender"],
                    doc.val()["receiver"],
                    doc.val()["file_path"],
                    doc.val()["priority"],
                    doc.val()["synced"],
                ]
                for idx, doc in enumerate(user_docs)
            ]

            print("\n", tabulate(table, headers), "\n")
