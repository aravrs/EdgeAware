import pickle

vectorizer = pickle.load(open("edgeaware/weights/vectorizer.pickel", "rb"))
model = pickle.load(open("edgeaware/weights/model.pickel", "rb"))


def predict(data):

    processed_input = vectorizer.transform([data["file_path"].split(".")[0]])

    prediction_id = model.predict(processed_input)[0]
    prediction_map = {1: "high", 2: "medium", 3: "low"}

    return prediction_map[prediction_id]
