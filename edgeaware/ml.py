# TODO: algo


def predict(data):
    print(data["file_path"])

    if data["file_path"].lower() in ["high", "important", "urgent", ".pdf", ".doc"]:
        return "high"

    elif data["file_path"].lower() in [".img"]:
        return "medium"

    else:
        return "low"
