$(document).ready(function() {

	// Define sockets
	var socket = io.connect('https://ide-cc53314679134f648784a767fd9887a4-8080.cs50.ws/');
	var bet_socket = io('https://ide-cc53314679134f648784a767fd9887a4-8080.cs50.ws/bet');

	// Reduce website hackability by defining variables pulled from the HTML as soon as possible
	let game = document.getElementById("game");
	let player = document.getElementById("player");
	let opponent = document.getElementById("opponent");
	let userCredits = document.getElementById("credits").innerHTML;

	// Create variables off of attributes of "meta" variables
	let game_id = parseInt(game.getAttribute("game_id"));
	let phase = game.getAttribute("phase");
	let player1_bet = game.getAttribute("player1_bet");
	let player2_bet = game.getAttribute("player2_bet");
	let player_turn = parseInt(game.getAttribute("player_turn"));

	let playerID = parseInt(player.getAttribute("player_id"));
	let player_phrase = player.getAttribute("player");

	let opponent_id = parseInt(opponent.getAttribute("opponent_id"));

	// Hide HTML that must be hidden from the beginning

	if (phase === "betting")
	{
		if (player_turn === playerID && (player1_bet === "None" || player1_bet === "null") && (player2_bet === "None" || player2_bet === "null") && player_phrase === "player1")
		{
			$("#p2FollowBet").hide();
			$("#betDiv").hide();
		}
		else if (player_turn != playerID)
		{
			$("#betPhase").hide();
		}
		else if (player_turn === playerID && player1_bet != "None" && player1_bet != "null" && (player2_bet === "None" || player2_bet === "null") && player_phrase === "player2")
		{
			let betTxt = "";
			if (parseInt(player1_bet) === 0)
			{
				betTxt = "Checks (bets 0 credits)";
			}
			else
			{
				betTxt = "bets " + player1_bet + " credits"
			}
			document.getElementById("p1BetAction").innerHTML = betTxt;
			$("#p1Bet").hide();
			$("#followBetDiv").hide();
		}
	}
	else
	{
		$("betDiv").hide();
	}

	// When client recieves a message through the bet_socket
	bet_socket.on('bet', function(data) {

		for (pair in data)
		{
			if (data[pair] === null)
			{
				game.setAttribute(pair.toString(), data[pair]);
			}
			else
			{
				game.setAttribute(pair.toString(), data[pair].toString());
			}
		}

		game = document.getElementById("game");
		game_id = parseInt(game.getAttribute("game_id"));
		phase = game.getAttribute("phase");
		player1_bet = game.getAttribute("player1_bet");
		player2_bet = game.getAttribute("player2_bet");
		player_turn = parseInt(game.getAttribute("player_turn"));

		if (phase != "betting")
		{
			location.reload();
		}

		if (data["game_id"] === game_id)
		{
			if (data["player1_bet"] != null && data["player2_bet"] === null)
			{
				if (playerID === data["player2_id"])
				{
					document.getElementById("opponent_credits").innerHTML = (parseInt(document.getElementById("opponent_credits").innerHTML) - data["player1_bet"]).toString();
					document.getElementById("hand_pot").innerHTML = (parseInt(document.getElementById("hand_pot").innerHTML) + data["player1_bet"]).toString();
					let betTxt = "";
					if (parseInt(player1_bet) === 0)
					{
						betTxt = "Checks (bets 0 credits)";
					}
					else
					{
						betTxt = "bets " + player1_bet + " credits";
					}
					document.getElementById("p1BetAction").innerHTML = betTxt;
					$("#betPhase").show();
					$("#p1Bet").hide()
					$("#followBetDiv").hide();
				}
				else if (playerID === data["player1_id"])
				{
					document.getElementById("credits").innerHTML = (parseInt(document.getElementById("credits").innerHTML) - data["player1_bet"]).toString();
					document.getElementById("hand_pot").innerHTML = (parseInt(document.getElementById("hand_pot").innerHTML) + data["player1_bet"]).toString();
				}
			}
		}
	});

	// Decide what to do for the betting phase
	$('#betActionBtn').on('click', function() {

		if (document.getElementById("betAction").value === "bet") {
			$("#betActionDiv").hide();
			$("#betDiv").show();
		}
		else if (document.getElementById("betAction").value === "check")
		{
			$("#betActionDiv").hide();
			data = {"game_id": game_id, "action": "bet", "amount": 0}
			bet_socket.emit("bet", data);
		}
		else
		{
			document.getElementById("invalidBetAction").innerHTML = "Invalid bet action - Please input a valid value (check or bet)";
		}

	});

	// Decide how much to bet
	$('#betBtn').on('click', function() {
		let credits = document.getElementById("betCredits").value;
		if (credits === "")
		{
			document.getElementById("invalidBetCredits").innerHTML = "Please input a number of credits you would like to bet(a positive integer 1 to " + userCredits + ")";
		}
		else if (isNaN(parseInt(credits)))
		{
			document.getElementById("invalidBetCredits").innerHTML = "Invalid amount of credits - Please input a valid number of credits (a positive integer 1 to " + userCredits + ")";
		}
		else if (credits < 1 || credits > parseInt(userCredits))
		{
			document.getElementById("invalidBetCredits").innerHTML = "Invalid amount of credits - Please input a valid number of credits (a positive integer 1 to " + userCredits + ")";
		}
		else
		{
			$("#betDiv").hide();
			data = {"game_id": game_id, "action": "bet", "amount": parseInt(credits)}
			bet_socket.emit("bet", data);
		}
	});



	// P2 decide how to follow up
	$('#followBetActionBtn').on('click', function() {

		if (document.getElementById("followBetAction").value === "call")
		{
			if (parseInt(player1_bet) > parseInt(game.getAttribute("player1_credits")))
			{
				document.getElementById("invalidFollowBetAction").innerHTML = "You can't call, you don't have enough credits!";
				return;
			}
			$("#followBetActionDiv").hide();
			data = {"game_id": game_id, "action": "call", "amount": parseInt(player1_bet)}
			bet_socket.emit("bet", data);
		}
		else if (document.getElementById("followBetAction").value === "fold")
		{
			$("#betActionDiv").hide();
			data = {"game_id": game_id, "action": "fold", "amount": 0}
			bet_socket.emit("bet", data);
		}
		// else if (document.getElementById("followBetAction").value === "raise")
		// {

		// }
		else
		{
			document.getElementById("invalidFollowBetAction").innerHTML = "Invalid bet action - Please input a valid value (raise, call, or fold)";
		}

		return;

	});

});