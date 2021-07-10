import os
import boto3
import pyrebase
from prettytable import PrettyTable

import edgeware.ml as ml


class Edgeware:
    # TODO: docstrings
    # TODO: exceptions
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
        print(f"Registered, {username}!")

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
            print(f"Logged in, {username}!")

    def reset_password(
        self,
        email,
    ):
        self.auth.send_password_reset_email(email)
        print(f"Password reset mail is sent to {email}")

    def registered(func):
        def check(self, *args, **kwargs):
            if self.user["registered"]:
                return func(self, *args, **kwargs)
            else:
                print("Please login!")

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
        print(f"Uploaded to bucket, {self.user_data['bucket_name']}!")

        # update meta
        self.db.child("docs").child(push_meta["name"]).update({"inS3_sender": True})

    def _get_docs(self, user, sender=False):
        all_docs = self.db.child("docs").get()

        # fetch where current user is receiver
        user_docs = []
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
        print("Syncing...")
        user_docs = self._get_docs(self.user_data["username"])

        # s3 functions
        for idx, doc in enumerate(user_docs):

            # force download given file id
            override = False
            if file_id is not None and file_id == str(idx):
                override = True

            if override or not doc.val()["synced"]:
                print(
                    f"[{idx}]",
                    f"Sender: {doc.val()['sender']}",
                    f"File: {doc.val()['file_path']}",
                    f"Priority: {doc.val()['priority']}",
                    f"Synced: {doc.val()['synced']}",
                )

                if override or doc.val()["priority"] == "low":
                    # *** do nothing *** #
                    print(f"File available in {doc.val()['sender']} bucket.")

                if override or (
                    doc.val()["priority"] in ["medium", "high"]
                    and doc.val()["inS3_receiver"] == False
                    and doc.val()["inS3_sender"] == True
                ):
                    # *** move from sender s3 to user s3 *** #

                    # download from sender s3
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

                    # upload to user s3
                    boto3.resource(
                        service_name="s3",
                        region_name=self.user_data["region_name"],
                        aws_access_key_id=self.user_data["aws_access_key_id"],
                        aws_secret_access_key=self.user_data["aws_secret_access_key"],
                    ).Bucket(self.user_data["bucket_name"]).upload_file(
                        Filename=doc.val()["file_path"], Key=doc.val()["file_path"]
                    )

                    # delete downloaded file
                    os.remove(doc.val()["file_path"])

                    # update meta
                    self.db.child("docs").child(doc.key()).update(
                        {"inS3_receiver": True}
                    )
                    print(
                        f"File available in your bucket, {self.user_data['bucket_name']}."
                    )

                if override or (
                    doc.val()["priority"] == "high"
                    and doc.val()["inLocal_receiver"] != True
                ):
                    # *** download to user's local machine *** #

                    boto3.resource(
                        service_name="s3",
                        region_name=self.user_data["region_name"],
                        aws_access_key_id=self.user_data["aws_access_key_id"],
                        aws_secret_access_key=self.user_data["aws_secret_access_key"],
                    ).Bucket(self.user_data["bucket_name"]).download_file(
                        Key=doc.val()["file_path"], Filename=doc.val()["file_path"]
                    )

                    # update meta
                    self.db.child("docs").child(doc.key()).update(
                        {"inLocal_receiver": True}
                    )
                    print(f"File available in your local machine.")

                self.db.child("docs").child(doc.key()).update({"synced": True})

        print("Sync complete.")

    def delete(self, file_id):
        print("Deleting...")
        user_docs = self._get_docs(self.user_data["username"], sender=True)

        for idx, doc in enumerate(user_docs):
            if file_id == str(idx):
                print(
                    f"[{idx}] " + f"Sender: {doc.val()['sender']}",
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
                        Delete={
                            "Objects": [
                                {"Key": doc.val()["file_path"]}  # the_name of_your_file
                            ]
                        }
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
                        Delete={
                            "Objects": [
                                {"Key": doc.val()["file_path"]}  # the_name of_your_file
                            ]
                        }
                    )
                    print(
                        f"File deleted from your bucket, {self.user_data['bucket_name']}"
                    )

                # firebase delete meta
                self.db.child("docs").child(doc.key()).remove()

                print("File deleted.")

    def check(self):
        user_docs = self._get_docs(self.user_data["username"], sender=True)

        if len(user_docs) < 1:
            print("No files found.")

        else:
            # tabulate sync meta data
            meta_table = PrettyTable(padding_width=5)
            meta_table.field_names = [
                "ID",
                "SENDER",
                "RECEIVER",
                "FILE",
                "PRIORITY",
                "SYNCED",
            ]

            for idx, doc in enumerate(user_docs):
                # update table
                meta_table.add_row(
                    [
                        idx,
                        doc.val()["sender"],
                        doc.val()["receiver"],
                        doc.val()["file_path"],
                        doc.val()["priority"],
                        doc.val()["synced"],
                    ]
                )

            print(meta_table)
