# Service Worker - Asynchronously manage data between buckets

import os, time
import json
import boto3
import pyrebase


def transfer(doc):

    if doc.val()["priority"] in ["medium", "high"]:

        if doc.val()["inS3_sender"] and not doc.val()["inS3_receiver"]:
            # transfer from sender's bucket to receiver

            # get data
            sender_data = (
                db.child("users").child(doc.val()["sender"]).get().each()[0].val()
            )
            receiver_data = (
                db.child("users").child(doc.val()["receiver"]).get().each()[0].val()
            )

            # download from sender's bucket
            boto3.resource(
                service_name="s3",
                region_name=sender_data["region_name"],
                aws_access_key_id=sender_data["aws_access_key_id"],
                aws_secret_access_key=sender_data["aws_secret_access_key"],
            ).Bucket(sender_data["bucket_name"]).download_file(
                Key=doc.val()["file_path"], Filename=doc.val()["file_path"]
            )

            # upload to receiver's bucket
            boto3.resource(
                service_name="s3",
                region_name=receiver_data["region_name"],
                aws_access_key_id=receiver_data["aws_access_key_id"],
                aws_secret_access_key=receiver_data["aws_secret_access_key"],
            ).Bucket(receiver_data["bucket_name"]).upload_file(
                Filename=doc.val()["file_path"], Key=doc.val()["file_path"]
            )

            # delete downloaded file
            os.remove(doc.val()["file_path"])

            # update meta
            db.child("docs").child(doc.key()).update({"inS3_receiver": True})

            print(
                f"{doc.val()['file_path']} : {sender_data['username']} -> {receiver_data['username']}"
            )

        if doc.val()["receiver"] and not doc.val()["inS3_sender"]:
            # transfer from receiver's bucket to sender

            # get data
            sender_data = (
                db.child("users").child(doc.val()["sender"]).get().each()[0].val()
            )
            receiver_data = (
                db.child("users").child(doc.val()["receiver"]).get().each()[0].val()
            )

            # download from receiver's bucket
            boto3.resource(
                service_name="s3",
                region_name=receiver_data["region_name"],
                aws_access_key_id=receiver_data["aws_access_key_id"],
                aws_secret_access_key=receiver_data["aws_secret_access_key"],
            ).Bucket(receiver_data["bucket_name"]).download_file(
                Key=doc.val()["file_path"], Filename=doc.val()["file_path"]
            )

            # upload to sender's bucket
            boto3.resource(
                service_name="s3",
                region_name=sender_data["region_name"],
                aws_access_key_id=sender_data["aws_access_key_id"],
                aws_secret_access_key=sender_data["aws_secret_access_key"],
            ).Bucket(sender_data["bucket_name"]).upload_file(
                Filename=doc.val()["file_path"], Key=doc.val()["file_path"]
            )

            # delete downloaded file
            os.remove(doc.val()["file_path"])

            # update meta
            db.child("docs").child(doc.key()).update({"inS3_receiver": True})

            print(
                f"{doc.val()['file_path']} : {receiver_data['username']} -> {sender_data['username']}"
            )


if __name__ == "__main__":

    print("starting transfer...")
    firebase = pyrebase.initialize_app(json.load(open("./config.json")))
    db = firebase.database()

    print("TRANSFER STARTED")

    while True:
        print("transferring...")

        all_docs = db.child("docs").get()
        if all_docs.each():
            for doc in all_docs.each():
                transfer(doc)

        time.sleep(1 * 60)  # transfer every 1 min(s)
