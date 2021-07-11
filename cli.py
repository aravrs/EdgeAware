import cmd, json
import warnings
from termcolor import colored

# hide warnings
warnings.filterwarnings("ignore")

from edgeaware import EdgeAware


ew = EdgeAware(json.load(open("./config.json")))

# helpers
def parse(arg):
    return tuple(map(str, arg.split()))


class EdgeAwareCLI(cmd.Cmd):
    intro = colored(
        "Welcome to EdgeAware shell. Type help or ? to list commands.", "cyan"
    )
    prompt = colored("edgeaware >> ", "cyan")
    file = None

    def handle(func):
        def handler(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                print(colored("Error! Please try again.", "red"))

        return handler

    @handle
    def do_register(self, arg):
        "Register:  email, username, password, aws_access_key_id, aws_secret_access_key, region_name, bucket_name"
        email = input("Email: ")
        username = input("Username: ")
        password = input("Password: ")
        aws_access_key_id = input("AWS Access Key ID: ")
        aws_secret_access_key = input("AWS Secret Access Key: ")
        region_name = input("Region Name: ")
        bucket_name = input("Bucket Name: ")
        ew.register(
            email,
            username,
            password,
            aws_access_key_id,
            aws_secret_access_key,
            region_name,
            bucket_name,
        )

    @handle
    def do_login(self, arg):
        "Login: username, password"
        ew.login(*parse(arg))

    @handle
    def do_reset_password(self, arg):
        "Reset Password: email"
        ew.reset_password(*parse(arg))

    @handle
    def do_send(self, arg):
        "Send: to_username, file_path, priority=None"
        ew.send(*parse(arg))

    @handle
    def do_delete(self, arg):
        "Delete: file_id"
        ew.delete(*parse(arg))

    @handle
    def do_check(self, arg):
        "Check"
        ew.check(*parse(arg))

    @handle
    def do_sync(self, arg):
        "Sync: file_id=None"
        ew.sync(*parse(arg))

    @handle
    def do_logout(self, arg):
        "Logout"
        print(colored("EdgeAware terminated.", "red"))
        return True

    # utils
    def do_record(self, arg):
        self.file = open(arg, "w")

    def do_playback(self, arg):
        self.close()
        with open(arg) as f:
            self.cmdqueue.extend(f.read().splitlines())

    def do_precmd(self, line):
        line = line.lower()
        if self.file and "playback" not in line:
            print(line, file=self.file)
        return line

    def do_close(self):
        if self.file:
            self.file.close()
            self.file = None


if __name__ == "__main__":
    EdgeAwareCLI().cmdloop()
