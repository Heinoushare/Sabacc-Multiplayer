from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_cors import CORS, cross_origin
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.datastructures import ImmutableMultiDict
from helpers import *
from dataHelpers import *
from alderaanHelpers import *
from flask_socketio import SocketIO, send, emit
import yaml

# Get config.yml data
config = {}
with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# CORS
link = config["DOMAIN"]
linkTwo = config["CROSS_ORIGIN"]

allowedCORS = [link, f"{link}/chat", f"{link}/game", f"{link}/bet", f"{link}/card", f"{link}/shift", f"{link}/protect", f"{link}/cont", linkTwo, f"{linkTwo}/chat", f"{linkTwo}/game", f"{linkTwo}/bet", f"{linkTwo}/card", f"{linkTwo}/shift", f"{linkTwo}/protect", f"{linkTwo}/cont"]

socketio = SocketIO(app, cors_allowed_origins=allowedCORS)

CORS(app, origins=allowedCORS)

# Declare dictionary to store key-value pairs of user ids and session ids
users = {}

sessions = {}

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///sabacc.db")




@socketio.on("message", namespace="/chat")
def handleMessage(msg):

    """ GalactiChat """

    # Broadcast the recieved message to all chatters
    send(msg, broadcast=True)

@app.route("/chat")
@login_required
def chat():

    """Global Chat using Socket.IO"""

    # Tell the client what their username is
    user_id = session.get("user_id")
    user = db.execute(f"SELECT * FROM users WHERE id = {user_id}")[0]


    return render_template("chat.html", user=user)




@socketio.on("game", namespace="/game")
def game_connect():

    """ Establish Game Socket Connection """

    user_id = session.get("user_id")
    if not user_id:
        return
    sid = request.sid
    users[user_id] = sid

""" REST APIs """

@app.route("/login", methods=["POST"])
@cross_origin()
def login():
    """Log user in"""

    # User reached route via POST
    if request.method == "POST":

        username = request.json.get("username")
        password = request.json.get("password")
        check = checkLogin(username, password)
        if check["status"] != 200:
            return jsonify({"message": check["message"]}), check["status"]

        # If the user wants to change their password, do so
        # change = request.json.get("change")
        # if change != None:

        #     # Check that passwords are valid
        #     newPassword = request.json.get("newPassword")
        #     if not newPassword:
        #         return jsonify({"message": "Missing new password"}), 401

        #     passCon = request.json.get("passCon")
        #     if not passCon:
        #         return apology("Missing new password confirmation") # TODO LEFT OFF HERE

        #     if password != passCon:
        #         return apology("New passwords do not match")

        #     # Change user's password
        #     passHash = str(generate_password_hash(password))
        #     db.execute(f"UPDATE users SET hash = ? WHERE username = ?", passHash, username)

        # Remember which user has logged in
        # session["user_id"] = rows[0]["id"]

        # # Set default themes
        # session["dark"] = False
        # session["theme"] = "rebels"

        # Redirect user to home page
        return jsonify({"message": "Logged in!"}), 200

    # User reached route via GET (as by clicking a link or via redirect)
    
@app.route("/", methods=["POST"])
@cross_origin()
def index():

    username = request.json.get("username")
    password = request.json.get("password")
    check = checkLogin(username, password)
    if check["status"] != 200:
        return jsonify({"message": check["message"]}), check["status"]
    
    # Get the user's id for later use
    user_id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]

    # Query the database for all the games
    games = db.execute("SELECT * FROM games")
    newGames = games.copy()

    user_ids = []
    player_turns = []

    # Remove games that have been completed and that are not relevant to the player
    for game in games:
        if str(user_id) not in game["player_ids"].split(",") or game["completed"] == True:
            newGames.remove(game)

        else:
            user_ids.append(game["player_ids"].split(","))
            player_turns.append(db.execute("SELECT username FROM users WHERE id = ?", game["player_turn"])[0]["username"])


    # Get all the relevant usernames from the database
    usernames = []
    for set in user_ids:
        s = ""
        for user in set:
            s += str(db.execute("SELECT * FROM users WHERE id = ?", int(user))[0]["username"]) + ", "

        st = s.strip(", ")

        usernames.append(st)

    # Render the home page with the user's active game data
    return jsonify({
        "games": newGames, 
        "usernames": usernames, 
        "gamesLen": len(newGames), 
        "player_turns": player_turns
        }), 200

@app.route("/register", methods=["POST"])
@cross_origin()
def register():
    """Register user"""

    if request.method == "POST":
        
        # Ensure username was submitted
        username = request.json.get("username")
        if not username:
            return jsonify({"message": "Must provide username"}), 401
        
        if " " in username:
            return jsonify({"message": "Please do not put spaces in your username"}), 401
        
        # Check that username has not already been taken
        if db.execute("SELECT * FROM users WHERE username = ?", username) != []:
            return jsonify({"message": "Username has already been taken"}), 401
        
        # Ensure password is valid
        password = request.json.get("password")
        if not password:
            return jsonify({"message": "Must provide password"}), 401

        confirmation = request.json.get("confirmPassword")

        if not confirmation:
            return jsonify({"message": "Must provide confirmation password"}), 401

        if confirmation != password:
            return jsonify({"message": "Confirmation and password do not match"}), 401
        
        if " " in password:
            return jsonify({"message": "Please do not put spaces in your password"}), 401

        # Complete registration
        passHash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, str(passHash))

        # Redirect user to home page
        return jsonify({"message": "Registered!"}), 200
    
@app.route("/game", methods=["POST"])
@cross_origin()
def game():
    """Play Sabacc!"""

    username = request.json.get("username")
    password = request.json.get("password")
    game_id = request.json.get("game_id")
    check = checkLogin(username, password)
    if check["status"] != 200:
        return jsonify({"message": check["message"]}), check["status"]
    
    # Get the user's id for later use
    user_id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]
    
    game = db.execute(f"SELECT * FROM games WHERE game_id = {game_id}")[0]

    yours = False
    for id in game["player_ids"].split(","):
        if id == str(user_id):
            yours = True
            break

    if yours == False:
        return jsonify({"message": "This is not one of your games"}), 403

    users = []
    for u in game["player_ids"].split(","):
        users.append(db.execute("SELECT id, username FROM users WHERE id = ?", int(u))[0]["username"])

    return jsonify({"message": "Good luck!", "gata": game, "users": users, "user_id": int(user_id)}), 200

@app.route("/host", methods=["POST"])
@cross_origin()
def host():
    """Make a new game of Sabacc"""

    if request.method == "POST":
    
        username = request.json.get("username")
        password = request.json.get("password")
        formPlayers = request.json.get("players")
        check = checkLogin(username, password)
        if check["status"] != 200:
            return jsonify({"message": check["message"]}), check["status"]
    
        user_id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]

        # Make list of players
        players = []
        players.append(user_id)

        # Check all eight player input boxes for player usernames

        if len(formPlayers) > 8:
            return jsonify({"message": "You can only have a maximum of eight players"}), 401

        for pForm in formPlayers:
            if pForm != "":
                p = db.execute(f"SELECT * FROM users WHERE username = ?", pForm)
                if len(p) == 0:
                    return jsonify({"message": f"Player {pForm} does not exist"}), 401
                if str(p[0]["id"]) == str(session.get("user_id")):
                    return jsonify({"message": "You cannot play with yourself"}), 401
                if p[0]["id"] in players:
                    return jsonify({"message": "All players must be different"}), 401
                players.append(p[0]["id"])

        # Pot size variables
        hPot = 0
        sPot = 0

        # Make list of credits
        credits = []
        for i in range(len(players)):
            credits.append(985)
            hPot += 5
            sPot += 10


        # Convert list data to strings
        playersStr = listToStr(players)
        creditsStr = listToStr(credits)

        # Protecteds
        prots = ""
        for i in range(len(players)):
            prots += "0,0;"

        prots = prots.strip(";")

        # Bets
        pBets = ""
        for i in range(len(players) - 1):
            pBets += ","

        # Construct deck and hands
        deckData = constructDeck(len(players))
        deck = deckData["deck"]
        handsStr = listToStr(deckData["hands"], sep=";")

        # Create game in database
        db.execute("INSERT INTO games (player_ids, player_credits, player_bets, hand_pot, sabacc_pot, deck, player_hands, player_protecteds, player_turn, p_act) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", playersStr, creditsStr, pBets, hPot, sPot, deck, handsStr, prots, user_id, "")

        # Get game ID
        game_id = db.execute("SELECT game_id FROM games WHERE player_ids = ? ORDER BY game_id DESC", playersStr)[0]["game_id"]

        return jsonify({"message": "Game hosted!", "redirect": f"/game/{game_id}"}), 200
    
@app.route("/protect", methods=["POST"])
@cross_origin()
def protect():

    username = request.json.get("username")
    password = request.json.get("password")
    check = checkLogin(username, password)
    if check["status"] != 200:
        return jsonify({"message": check["message"]}), check["status"]

    user_id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]

    # Set some variables for the whole function
    game_id = request.json.get("game_id")
    protect = request.json.get("protect")
    game = db.execute("SELECT * FROM games WHERE game_id = ?", game_id)[0]
    uName = db.execute("SELECT username FROM users where id = ?", user_id)[0]["username"]
    uDex = game["player_ids"].split(",").index(str(user_id))
    u_hand = game["player_hands"].split(";")[uDex]


    # Check if card being protected is in hand
    cardDex = -1
    handL = u_hand.split(",")
    for card in handL:
        if card == protect:
            cardDex = handL.index(card)
            break


    if cardDex == -1:
        print("NON-MATCHING USER INPUT")
        return jsonify({"message": "non matching user input"}), 401
    
    # Card is confirmed to be in hand


    # Create new List of protected cards
    protectedAll = game["player_protecteds"].split(";")
    protsStr = protectedAll[uDex]
    protsList = protsStr.split(",")
    protsList[cardDex] = 1

    # Convert that List to a String
    protsStr = listToStr(protsList)
    protectedAll[uDex] = protsStr

    protAllStr = listToStr(protectedAll, sep=";")

    # Update the database
    db.execute(f"UPDATE games SET player_protecteds = ?, p_act = ? WHERE game_id = {game_id}", protAllStr, f"{uName} protected a card")

    # Tell Clients to refresh data

    gata = db.execute(f"SELECT * FROM games WHERE game_id = {game_id}")[0]
        
    return jsonify({"message": "Card protected", "gata": gata}), 200

""" Gameplay REST APIs """

@app.route("/bet", methods=["POST"])
@cross_origin()
def bet():

    username = request.json.get("username")
    password = request.json.get("password")
    check = checkLogin(username, password)
    if check["status"] != 200:
        return jsonify({"message": check["message"]}), check["status"]

    user_id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]

    # Set some variables for the whole function
    game_id = request.json.get("game_id")
    game = db.execute("SELECT * FROM games WHERE game_id = ?", game_id)[0]
    action = request.json.get("action")
    amount = request.json.get("amount")
    users = game["player_ids"].split(",")
    uName = db.execute("SELECT username FROM users where id = ?", user_id)[0]["username"]
    u_dex = game["player_ids"].split(",").index(str(user_id))
    creditsStr = game["player_credits"]
    betsStr = game["player_bets"]

    endRound = False
    foldEnd = False

    if game["phase"] != "betting":
        return

    player = ""
    if users.index(str(user_id)) == 0:
        player = "player1"

    # If it is not this player's turn
    if game["player_turn"] != int(user_id):
        return

    # If player 1 bets or checks
    if action == "bet" and player == "player1":

        pCredits = int(strListRead(creditsStr, 0))
        newCredits = strListMod(creditsStr, 0, pCredits - amount)

        newBets = strListMod(betsStr, 0, amount)

        act = uName
        if amount == 0:
            act += " checks"
        elif amount != 0:
            act += f" bets ${amount}"

        db.execute(f"UPDATE games SET player_credits = ?, player_bets = ?, player_turn = ?, p_act = ? WHERE game_id = {game_id}", newCredits, newBets, int(users[1]), act)


    elif action == "call":

        pCredits = int(strListRead(creditsStr, u_dex))
        newCredits = strListMod(creditsStr, u_dex, pCredits - amount)

        newBets = strListMod(betsStr, u_dex, amount + readIntValStrList(betsStr, u_dex))

        nextPlayer = u_dex + 1

        if str(user_id) == users[len(users) - 1]:
            endRound = True


        if endRound == False and readIntValStrList(newBets, nextPlayer) == readIntValStrList(newBets, u_dex):

            if nextPlayer == len(users) - 1:
                endRound = True

            nextPlayer += 1

        if endRound == True:
            nextPlayer = 0

        db.execute(f"UPDATE games SET player_credits = ?, player_bets = ?, player_turn = ?, p_act = ? WHERE game_id = {game_id}", newCredits, newBets, int(users[nextPlayer]), f"{uName} calls")

    elif action == "raise":

        pCredits = int(strListRead(creditsStr, u_dex))
        newCredits = strListMod(creditsStr, u_dex, pCredits - amount)

        newBets = strListMod(betsStr, u_dex, amount + readIntValStrList(betsStr, u_dex))

        nextPlayer = 0

        if str(user_id) == users[0]:
            nextPlayer = 1

        db.execute(f"UPDATE games SET player_credits = ?, player_bets = ?, player_turn = ?, p_act = ? WHERE game_id = {game_id}", newCredits, newBets, int(users[nextPlayer]), f"{uName} raises to ${newBets.split(',')[u_dex]}")


    elif action == "fold":

        newPlayers = strListPop(game["player_ids"], u_dex)
        newHands = strListPop(game["player_hands"], u_dex, sep=";")
        newProtecteds = strListPop(game["player_protecteds"], u_dex, sep=";")
        newCredits = strListPop(creditsStr, u_dex,)
        newBets = strListPop(betsStr, u_dex)

        newFoldedP = strListAppend(game["folded_players"], user_id)

        newFoldedC = strListAppend(game["folded_credits"], int(strListRead(creditsStr, u_dex)) + int(strListRead(betsStr, u_dex, default=0)))

        foldEnd = False

        if len(newPlayers.split(",")) == 1:
            foldEnd = True

        nextPlayer = u_dex

        if str(user_id) == users[len(users) - 1]:
            endRound = True

        if endRound == True:
            nextPlayer = 0

        db.execute(f"UPDATE games SET player_ids = ?, player_credits = ?, player_bets = ?, player_hands = ?, player_protecteds = ?, player_turn = ?, folded_players = ?, folded_credits = ?, p_act = ? WHERE game_id = {game_id}", newPlayers, newCredits, newBets, newHands, newProtecteds, int(newPlayers.split(",")[nextPlayer]), newFoldedP, newFoldedC, f"{uName} folds")

    game = db.execute(f"SELECT * FROM games WHERE game_id = {game_id}")[0]
    users = game["player_ids"].split(",")
    creditsStr = game["player_credits"]
    betsStr = game["player_bets"]

    if foldEnd == True:

        newCredits = creditsStr
        newCredits = strListMod(creditsStr, 0, int(strListRead(creditsStr, 0)) + game["hand_pot"] + int(strListRead(betsStr, 0)))

        db.execute(f"UPDATE games SET player_credits = ?, player_bets = ?, hand_pot = ?, player_turn = ?, completed = ? WHERE game_id = {game_id}", newCredits, "", 0, int(users[0]), True)

    game = db.execute(f"SELECT * FROM games WHERE game_id = {game_id}")[0]
    users = game["player_ids"].split(",")
    creditsStr = game["player_credits"]
    betsStr = game["player_bets"]

    if endRound == True:
        
        betsSum = 0

        newBets = ""
        for i in range(len(users) - 1):
            newBets += ","

        for i in range(len(users)):

            try:
                betsSum += int(strListRead(betsStr, i))
            except ValueError:
                pass

        if foldEnd == True:
            betsSum = 0

        db.execute(f"UPDATE games SET player_bets = ?, hand_pot = ?, phase = ?, player_turn = ? WHERE game_id = {game_id}", newBets, game["hand_pot"] + betsSum, "card", int(users[0]))

    # Tell Client to refresh data
    gata = db.execute(f"SELECT * FROM games WHERE game_id = {game_id}")[0]
    
    return jsonify({"message": "Bet!", "gata": gata}), 200

@app.route("/card", methods=["POST"])
@cross_origin()
def card():

    username = request.json.get("username")
    password = request.json.get("password")
    check = checkLogin(username, password)
    if check["status"] != 200:
        return jsonify({"message": check["message"]}), check["status"]

    user_id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]

    # Set some variables for the whole function
    game_id = request.json.get("game_id")
    game = db.execute("SELECT * FROM games WHERE game_id = ?", game_id)[0]
    action = request.json.get("action")
    tradeCard = request.json.get("trade")

    users = game["player_ids"].split(",")
    uName = db.execute("SELECT username FROM users where id = ?", user_id)[0]["username"]
    u_dex = game["player_ids"].split(",").index(str(user_id))

    deckStr = game["deck"]
    handsStr = game["player_hands"]
    handsList = handsStr.split(";")
    protsStr = game["player_protecteds"]
    protsList = protsStr.split(";")
    handPot = game["hand_pot"]
    creditsStr = game["player_credits"]

    endRound = False
    endGame = False

    if game["phase"] != "card" and game["phase"] != "alderaan":
        return

    player = ""
    if users.index(str(user_id)) == 0:
        player = "player1"

    # If it is not this player's turn
    if game["player_turn"] != int(user_id):
        return
    
    if action == "draw":
        drawData = drawCard(deckStr)
        newDeck = drawData["deck"]
        newCard = drawData["card"]
        handsList[u_dex] += "," + newCard
        newHands = listToStr(handsList, sep=";")

        protsList[u_dex] += ",0"
        newProts = listToStr(protsList, sep=";")

        nextPlayer = u_dex + 1

        if str(user_id) == users[len(users) - 1]:
            endRound = True

        if endRound == True:
            nextPlayer = 0


        db.execute(f"UPDATE games SET deck = ?, player_hands = ?, player_protecteds = ?, player_turn = ?, p_act = ? WHERE game_id = {game_id}", newDeck, newHands, newProts, int(users[nextPlayer]), f"{uName} draws")

    elif action == "trade":

        tradeDex = handsList[u_dex].split(",").index(tradeCard)

        drawData = drawCard(deckStr)
        newDeck = drawData["deck"]
        newCard = drawData["card"]
        handsList[u_dex] = strListMod(handsList[u_dex], tradeDex, newCard)
        newHands = listToStr(handsList, sep=";")

        protsList[u_dex] = strListMod(protsList[u_dex], tradeDex, "0")
        newProts = listToStr(protsList, sep=";")

        nextPlayer = u_dex + 1

        if str(user_id) == users[len(users) - 1]:
            endRound = True

        if endRound == True:
            nextPlayer = 0


        db.execute(f"UPDATE games SET deck = ?, player_hands = ?, player_protecteds = ?, player_turn = ?, p_act = ? WHERE game_id = {game_id}", newDeck, newHands, newProts, int(users[nextPlayer]), f"{uName} trades")

    elif action == "stand":

        nextPlayer = u_dex + 1

        if str(user_id) == users[len(users) - 1]:
            endRound = True

        if endRound == True:
            nextPlayer = 0


        db.execute(f"UPDATE games SET player_turn = ?, p_act = ? WHERE game_id = {game_id}", int(users[nextPlayer]), f"{uName} stands")


    elif action == "alderaan" and game["cycle_count"] != 0:

        nextPlayer = u_dex + 1

        if str(user_id) == users[len(users) - 1]:
            endGame = True

        if endGame == True:
            nextPlayer = 0


        db.execute(f"UPDATE games SET phase = ?, player_turn = ?, p_act = ? WHERE game_id = {game_id}", "alderaan", int(users[nextPlayer]), f"{uName} calls Alderaan")


    game = db.execute(f"SELECT * FROM games WHERE game_id = {game_id}")[0]
    users = game["player_ids"].split(",")
    handsStr = game["player_hands"]
    handsList = handsStr.split(";")
    protsStr = game["player_protecteds"]
    protsList = protsStr.split(";")
    deckStr = game["deck"]

    if endRound == True:

        newCycleCount = game["cycle_count"] + 1

        if game["phase"] == "alderaan":
            endGame = True

        else:

            newHands = handsStr
            newProtecteds = protsStr


            shift = rollShift()

            if shift == True:
                drawCounts = []
                hCards = []
                for k in range(len(handsList)):
                    drawCount = 0
                    newHandList = handsList[k].split(",")
                    newProtsList = protsList[k].split(",")

                    for p in range(len(protsList[k].split(","))):

                        if protsList[k].split(",")[p] == "0":
                            newHandList.remove(handsList[k].split(",")[p])
                            newProtsList.remove(protsList[k].split(",")[p])
                            drawCount += 1
                        else:
                            hCards.append(handsList[k].split(",")[p])

                    newHands = strListMod(newHands, k, listToStr(newHandList), sep=";")
                    newProtecteds = strListMod(newProtecteds, k, listToStr(newProtsList), sep=";")
                    drawCounts.append(drawCount)

                deckStr = shuffleDeck(hCards)

                handsList = newHands.split(";")
                
                protsList = newProtecteds.split(";")

                for i in range(len(handsList)):

                    for c in range(drawCounts[i]):
                        drawData = drawCard(deckStr)
                        deckStr = drawData["deck"]
                        newCard = drawData["card"]
                        handsList[i] += "," + newCard
                        handsList[i] = handsList[i].strip(",")
                        newHands = listToStr(handsList, sep=";")

                        protsList[i] += ",0"
                        protsList[i] = protsList[i].strip(",")
                        newProtecteds = listToStr(protsList, sep=";")

            shiftStr = ""
            if shift == True:
                shiftStr = "Sabacc shift!"
            elif shift == False:
                shiftStr = "No shift!"




            db.execute(f"UPDATE games SET phase = ?, deck = ?, player_hands = ?, player_protecteds = ?, player_turn = ?, cycle_count = ?, shift = ?, p_act = ? WHERE game_id = {game_id}", "betting", deckStr, newHands, newProtecteds, int(users[0]), newCycleCount, shift, shiftStr)


    if endGame == True:

        alderaanData = alderaanEnd(handsList, deckStr, protsList, False)

        newHands = listToStr(alderaanData["handsList"], sep=";")
        newDeck = listToStr(alderaanData["deck"])
        newProtecteds = listToStr(alderaanData["protsList"], sep=";")
        winnerDex = alderaanData["winner"]
        winnerVal = alderaanData["winnerVal"]

        handVals = calcHandVals(alderaanData["handsList"])
        bombOutDexes = []

        for val in handVals:
            if (val == 0 or abs(val) > 23) and val != winnerVal:
                bombOutDexes.append(handVals.index(val))

        newSabaccPot = game["sabacc_pot"]
        bombOutPrice = int(round((handPot * 0.1)))
        for b in bombOutDexes:
            creditsStr = strListMod(creditsStr, b, int(strListRead(creditsStr, b)) - bombOutPrice)
            newSabaccPot += bombOutPrice

        winStr = ""

        if winnerDex != -1:
            creditsStr = strListMod(creditsStr, winnerDex, int(strListRead(creditsStr, winnerDex)) + handPot)
            if abs(winnerVal) == 23 or winnerVal == 230:
                creditsStr = strListMod(creditsStr, winnerDex, int(strListRead(creditsStr, winnerDex)) + newSabaccPot)
                newSabaccPot = 0

            winner = db.execute(f"SELECT username FROM users where id = {int(users[winnerDex])}")[0]["username"]
            winStr = f"{winner} wins!"
        
        elif winnerDex == -1:
            newSabaccPot += handPot
            winStr = "Everyone bombs out and loses!"
            

        


        db.execute(f"UPDATE games SET player_credits = ?, hand_pot = ?, sabacc_pot = ?, deck = ?, player_hands = ?, player_protecteds = ?, player_turn = ?, p_act = ?, completed = ? WHERE game_id = {game_id}", creditsStr, 0, newSabaccPot, newDeck, newHands,  newProtecteds, int(users[0]), winStr, True)

    # Tell Client to refresh data
    gata = db.execute(f"SELECT * FROM games WHERE game_id = {game_id}")[0]
    
    return jsonify({"message": "Card!", "gata": gata}), 200

@app.route("/cont", methods=["POST"])
@cross_origin()
def cont():

    username = request.json.get("username")
    password = request.json.get("password")
    check = checkLogin(username, password)
    if check["status"] != 200:
        return jsonify({"message": check["message"]}), check["status"]

    user_id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]

    # Set some variables for the whole function
    game_id = request.json.get("game_id")
    game = db.execute("SELECT * FROM games WHERE game_id = ?", game_id)[0]

    creditsStr = game["player_credits"]
    users = game["player_ids"].split(",")

    if game["completed"] != True:
        return

    # If it is not this player's turn
    if game["player_turn"] != int(user_id):
        return
    
    newPlayers = game["player_ids"]
    if game["folded_players"] != None:
        newPlayers += "," + game["folded_players"]

    newPlayers = newPlayers.strip(",")
    users = newPlayers.split(",")

    # Rotate "Dealer"
    users = shiftList(users)
    newPlayers = listToStr(users)

    newCredits = creditsStr
    if game["folded_credits"] != None:
        newCredits += "," + game["folded_credits"]

    newCredits = newCredits.strip(",")
    creditsList = newCredits.split(",")

    # Rotate "Dealer" credits
    creditsList = shiftList(creditsList)
    newCredits = listToStr(creditsList)

    for c in creditsList:
        creditsList[creditsList.index(c)] = str(int(c) - 15)
    
    newCredits = listToStr(creditsList)

    hPot = 5 * len(users)
    sPot = game["sabacc_pot"] + (10 * len(users))

    # Protecteds
    prots = ""
    for i in range(len(users)):
        prots += "0,0;"

    prots = prots.strip(";")

    # Bets
    pBets = ""
    for i in range(len(users) - 1):
        pBets += ","

    # Construct deck and hands
    deckData = constructDeck(len(users))
    deck = deckData["deck"]
    handsStr = listToStr(deckData["hands"], sep=";")

    # Create game in database
    db.execute(f"UPDATE games SET player_ids = ?, player_credits = ?, player_bets = ?, hand_pot = ?, sabacc_pot = ?, phase = ?, deck = ?, player_hands = ?, player_protecteds = ?, player_turn = ?, folded_players = ?, folded_credits = ?, cycle_count = ?, p_act = ?, completed = ? WHERE game_id = {game_id}", newPlayers, newCredits, pBets, hPot, sPot, "betting", deck, handsStr, prots, int(users[0]), None, None, 0, "", False)

    # Tell Client to refresh data
    gata = db.execute(f"SELECT * FROM games WHERE game_id = {game_id}")[0]
    
    return jsonify({"message": "Card!", "gata": gata}), 200

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
