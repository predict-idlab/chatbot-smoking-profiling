import chatbot

def new_question(db, id):
    db.questions.update_one({"user_id": id}, {"$set": {"status": True}})
    doc = db.questions.find_one({"user_id": id, "status": True})
    return doc["question"]


def questions(message, db, id):
    doc = db.questions.find_one({"user_id": id})
    if doc != None:
        current_question = db.questions.find_one({"user_id": id, "status": True})
        if current_question != None:
            try:
                if float(message) in [0, 0.2, 0.4, 0.6, 0.8, 1]:
                    module = current_question["module"]
                    duo = db.triggers.find_one({"user_id": id})[module]
                    tr = duo["triggers"]
                    level = duo["confidence_levels"]
                    tr.append(current_question["data"])
                    level.append(message)
                    db.triggers.update_one({"user_id": id}, {"$set": {module: {"triggers": tr, "confidence_levels": level}}})
                    db.questions.delete_many({"user_id": id, "status": True})
                    if (db.questions.count_documents({"user_id": id}) != 0):
                        return new_question(db, id)
                    else:
                        return chatbot.choose_game(db, id)
                else:
                    question = current_question["question"]
                    question["text"] = "Please select one of the following options. "+current_question["question"]["text"]
                    return question
            except:
                question = current_question["question"]
                question["text"] = "Please select one of the following options. "+current_question["question"]["text"]
                return current_question["question"]
        else:
            return new_question(db, id)
    else:
        return chatbot.choose_game(db, id)