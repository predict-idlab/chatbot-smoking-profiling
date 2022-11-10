import numpy as np
import JustOneLie.justonelie as justonelie

qr_options = [{"content_type":"text", "title": "Always", "payload": 1}, {"content_type":"text", "title": "Usually", "payload": 0.8}, 
        {"content_type":"text", "title": "Often", "payload": 0.6}, {"content_type":"text", "title": "Sometimes", "payload": 0.4},
        {"content_type":"text", "title": "Rarely", "payload": 0.2}, {"content_type":"text", "title": "Never", "payload": 0}]

casting = {0:"Never", 0.2:"Rarely", 0.4:"Sometimes", 0.6:"Often", 0.8:"Usually", 1:"Always"}
casting_inv = {"Never":0, "Rarely": 0.2, "Sometimes": 0.4, "Often": 0.6, "Usually": 0.8, "Always": 1}

def chatbot_analysis_guess(db, id, module):
    doc = db.triggers.find_one({"user_id":id})
    dic = doc[module]
    scores = dic["confidence_levels"]
    avg = 0.5
    if scores != []:
        avg = sum(scores)/len(scores)
    l = list(casting.keys())
    differences = [abs(i-avg) for i in l]
    index = np.argmin(differences)
    return casting[l[index]]

def chatbot_question(db, id):
    doc = db.questions.find_one({"user_id": id})
    guess = chatbot_analysis_guess(db, id, doc["module"])
    mes = doc["question"]["text"] + f"\n\nI observed you for a while now and I think the answer is: '{guess}'. Am I correct?"
    db.justonelie.update_one({"user_id": id}, {"$set": {"question_id": doc["_id"], "guess": guess}})
    qr = [{"content_type":"text", "title": "Yes", "payload": "yes"}, {"content_type":"text", "title": "No", "payload": "no"}]
    return {"text": mes, "quick_replies": qr}

def verify_chatbot_question(db, id, message):
    doc = db.justonelie.find_one({"user_id": id})
    doc_question = db.questions.find_one({"_id": doc["question_id"]})
    if message.lower() == "yes":
        duo = db.triggers.find_one({"user_id": id})[doc_question["module"]]
        tr = duo["triggers"] + [doc_question["data"]]
        level = duo["confidence_levels"] + [casting_inv[doc["guess"]]]
        db.triggers.update_one({"user_id": id}, {"$set": {doc_question["module"]: {"triggers": tr, "confidence_levels": level}}})
        db.questions.delete_one({"_id":doc["question_id"]})
        return justonelie.award_points("I analyzed you correctly!",id,db,20)
    else:
        justonelie.update_state(db.justonelie, id, "correction")
        return {"text": "My analysis is wrong, I shall collect more data to infer better estimations in the future. What is the correct answer?", "quick_replies": qr_options}

def correction_question(db, id, message):
    try:
        if float(message) not in casting.keys():
            return {"text": "Choose one of the 6 options. If you're on a phone, swipe to the right to find more options.", "quick_replies": qr_options}
        else:
            doc = db.justonelie.find_one({"user_id": id})
            doc_question = db.questions.find_one({"_id": doc["question_id"]})
            duo = db.triggers.find_one({"user_id": id})[doc_question["module"]]
            tr = duo["triggers"] + [doc_question["data"]]
            level = duo["confidence_levels"] + [float(message)]
            db.triggers.update_one({"user_id": id}, {"$set": {doc_question["module"]: {"triggers": tr, "confidence_levels": level}}})
            db.questions.delete_one({"_id":doc["question_id"]})
            return justonelie.award_points("I failed to infer your smoking trigger.",id,db,100)
    except:
        return {"text": "Choose one of the 6 options. If you're on a phone, swipe to the right to find more options.", "quick_replies": qr_options}