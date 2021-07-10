# TODO: algo


def predict(data):
    print(data["file_path"])

    if data["file_path"].lower() in ["high", "important", "urgent"]:
        return "H"

    elif data["file_path"].lower() in [".pdf", ".doc"]:
        return "M"

    else:
        return "L"
