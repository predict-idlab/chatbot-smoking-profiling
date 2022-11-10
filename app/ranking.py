
def get_ranking_dictionary(col):
    cursor = col.find({})
    dic = {}
    for doc in cursor:
        dic[doc["user_id"]] = doc["points"]   
    return dic

def print_ranking(listing, points, game):
    n = len(listing)
    total = n
    em = f"\n\nThe ranking in {game} is the following:\n"
    if n > 10:
        n = 10
    assigned = False
    for i, el in enumerate(listing[:n]):
        em += f"{i+1}. {el} points"
        if el == points and assigned == False:
            em += " (You)"
            assigned = True
        em += "\n"
    
    ranking = 0
    if points in listing:
        ranking = listing.index(points) + 1
        if ranking > 10:
            em += f"\n{ranking}) {points} points (You)\n"
        em += f"\nYou're in place {ranking} out of {total}."
        if ranking > 1:
            former = listing[ranking-2]
            em += f" To catch up to the one above you in ranking, you need to gain {former-points} points.\n"
        em += "\n"
    return em + "\n"

def get_ranking(id, db, game):
    col = db.justonelie
    if game == 'listbuilder':
        col = db.listbuilder
    elif game == 'storybuilder':
        col = db.storybuilder
    elif game == 'whereami':
        col = db.whereami
    points = col.find_one({"user_id": id})["points"]
    listing = list(get_ranking_dictionary(col).values())
    listing.sort(reverse=True)
    return print_ranking(listing, points, game)

def get_general_ranking(id, db):
    justonelie = get_ranking_dictionary(db.justonelie)
    listbuilder = get_ranking_dictionary(db.listbuilder)
    storybuilder = get_ranking_dictionary(db.storybuilder)
    whereami = get_ranking_dictionary(db.whereami)
    
    ids = list(dict.fromkeys(list(justonelie.keys()) + list(listbuilder.keys()) + list(storybuilder.keys()) + list(whereami.keys())))

    dic = {}
    for i in ids:
        dic[i] = 0
        if i in justonelie:
            dic[i] += justonelie[i]
        if i in listbuilder:
            dic[i] += listbuilder[i]
        if i in storybuilder:
            dic[i] += storybuilder[i]
        if i in whereami:
            dic[i] += whereami[i]
    
    listing = list(dic.values())
    listing.sort(reverse=True)

    points = 0
    if id in dic:
        points = dic[id]
    else:
        listing.append(points)

    return print_ranking(listing, points, "general")
