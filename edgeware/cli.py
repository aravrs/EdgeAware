import cmd, json
from .edgeware import Edgeware


ew = Edgeware(json.load(open("../config.json")))

# helpers
def parse(arg):
    return tuple(map(str, arg.split()))


class EdgewareCLI(cmd.Cmd):
    intro = "Welcome to Edgeware shell. Type help or ? to list commands.\n"
    prompt = "edgeware >> "
    file = None

    def register(self, arg):
        "Register:  email, username, password, aws_access_key_id, aws_secret_access_key, region_name, bucket_name"
        ew.register(*parse(arg))

    def login(self, arg):
        "Login: username, password"
        ew.login(*parse(arg))

    def reset_password(self, arg):
        "Reset Password: email"
        ew.reset_password(*parse(arg))

    def send(self, arg):
        "Send: to_username, file_path, priority=None"
        ew.send(*parse(arg))

    def logout(self, arg):
        "Stop recording, close the turtle window, and exit:  BYE"
        print("Edgeware terminated.")
        self.close()
        return True

    # utils
    def record(self, arg):
        "Save future commands to filename:  RECORD file.cmd"
        self.file = open(arg, "w")

    def playback(self, arg):
        "Playback commands from a file:  PLAYBACK file.cmd"
        self.close()
        with open(arg) as f:
            self.cmdqueue.extend(f.read().splitlines())

    def precmd(self, line):
        line = line.lower()
        if self.file and "playback" not in line:
            print(line, file=self.file)
        return line

    def close(self):
        if self.file:
            self.file.close()
            self.file = None


if __name__ == "__main__":
    EdgewareCLI().cmdloop()
