import boto3
import pyrebase


class Edgeware:
    def __init__(self, firebaseConfig):
        self.user = None
        self.user_data = None

        firebase = pyrebase.initialize_app(firebaseConfig)
        self.auth = firebase.auth()
        self.db = firebase.database()

    # def initialize(self, firebaseConfig):
    #     firebase = pyrebase.initialize_app(firebaseConfig)
    #     self.auth = firebase.auth()
    #     self.db = firebase.database()

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
            "username": username,  # TODO: check, to be unique
            "email": email,
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "region_name": region_name,
            "bucket_name": bucket_name,
        }
        self.db.child("users").child(username).push(
            self.user_data, self.user["idToken"]
        )
        print("Registered!")

    def login(self, username, password):
        db_user_data = self.db.child("users").child(username).get().each()[0].val()

        self.user = self.auth.sign_in_with_email_and_password(
            email=db_user_data["email"], password=password
        )

        if self.is_auth():
            self.user_data = db_user_data
            print("Logged in!")

    def reset_password(self, email):
        self.auth.send_password_reset_email(email)

    def is_auth(self):
        return self.user["registered"]

    def send(self, to_username, file_path, priority=None):

        # update meta
        data = {
            "sender": self.user_data["username"],
            "receiver": to_username,
            "file_path": file_path,
            "priority": None,
            "inS3_sender": True,
            "inS3_receiver": False,
            "inLocal_sender": False,
            "inLocal_receiver": False,
        }
        push_meta = self.db.child("docs").push(data)

        # update meta
        if priority is None:
            # priority = predict(data) # TODO: ML model
            priority = "H"
            pass

        self.db.child("docs").child(push_meta["name"]).update({"priority": priority})
        print("File tracked!")

        # upload user s3
        boto3.resource(
            service_name="s3",
            region_name=self.user_data["region_name"],
            aws_access_key_id=self.user_data["aws_access_key_id"],
            aws_secret_access_key=self.user_data["aws_secret_access_key"],
        ).Bucket(self.user_data["bucket_name"]).upload_file(
            Filename=file_path, Key=file_path
        )
        print("Uploaded to bucket!")

        # update meta
        self.db.child("docs").child(push_meta["name"]).update({"inS3_sender": True})

    def sync(self):
        all_docs = self.db.child("docs").get()  # TODO: if possible filter and fetch

        # fetch where current user is receiver
        user_docs = []
        for doc in all_docs.each():
            if doc.val()["receiver"] == self.user_data["username"]:
                print(doc.val())
                user_docs.append(doc)

        # s3 functions
        for doc in user_docs:

            if doc.val()["priority"] == "L":
                # placeholder
                pass

            if (
                doc.val()["priority"] in ["M", "H"]
                and doc.val()["inS3_receiver"] == False
                and doc.val()["inS3_sender"] == True
            ):

                # move to sender s3 to user s3

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

                # update meta
                self.db.child("docs").child(doc.key()).update({"inS3_receiver": True})

            if doc.val()["priority"] == "H" and doc.val()["inLocal_receiver"] != True:
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