
var connected = false;
var reconnectAttempts = 0;
var maxReconnectAttempts = 5;
var ws = null;

function wsConnect() {
	if (!connected) {
		reconnectAttempts = 0;
		startWebsocket();
	}
}

function startWebsocket() {
	var websocket_url = "ws://" + location.host + "/ws?token=" + encodeURIComponent(localStorage.getItem("session_token"));
	console.log("Connecting to WebSocket at: " + websocket_url);
	ws = new WebSocket(websocket_url);

	ws.onopen = function () {
		console.log("WebSocket connection established.");
		connected = true;
		reconnectAttempts = 0;

		// Load Settings and Media sections on connect
		sendCommand('FETCH_SETTINGS');
		sendCommand('FETCH_MEDIA_DIRS');
	}

	ws.onclose = function () {
		onWebSocketClose();
	};

	ws.onerror = function (error) {
		console.error("WebSocket error: ", error);
		ws.close();
	};

	ws.onmessage = function (event) {
		var obj = JSON.parse(event.data);
        if (obj.hasOwnProperty("force_logout") && obj["force_logout"] === true) {
            handleLogout("Server error received: " + obj["error"]);
		} else if (obj.hasOwnProperty("type") && obj["type"] === "log") {
			// Handle log message
			addLogEntry(obj);
		} else if (obj.hasOwnProperty("type") && obj["type"] === "session_update") {
			// Handle session update
			updateSessionInfo(obj);
		} else if (obj.hasOwnProperty("type") && obj["type"] === "session_info") {
			// Handle full session info receipt
			loadSessionInfo(obj);
		} else if (obj.hasOwnProperty("type") && obj["type"] === "altitude_update") {
			// Handle altitude update
			updateAltitudeInfo(obj); 
		} else if (obj.hasOwnProperty("type") && obj["type"] === "pan_tilt_update") {
			// Handle pan/tilt update
			updatePanTiltInfo(obj);
		} else if (obj.hasOwnProperty("type") && obj["type"] === "session_end") {
			// Handle session end
			endCaptureSession(obj);
		}  else if (obj.hasOwnProperty("type") && obj["type"] === "settings_update") {
			// Handle settings update
			loadSettings(obj);
		} else if (obj.hasOwnProperty("type") && obj["type"] === "media_dirs_update") {
			// Handle media directories update
			loadMediaSessionDirectories(obj);
		} else if (obj.hasOwnProperty("type") && obj["type"] === "media_file_paths") {
			// Handle media file path receipt
			loadMedia(obj);
		} else {
			console.warn("Received unknown WebSocket message: ", obj);
		}
	};
}

function onWebSocketClose() {
	connected = false;
	reconnectAttempts++;
	if (reconnectAttempts >= maxReconnectAttempts) {
		handleLogout("Maximum reconnect attempts reached.");
	} else {
		console.log("WebSocket connection closed. Attempting to reconnect ... (Attempt " + reconnectAttempts + "/" + maxReconnectAttempts + ")");
		setTimeout(startWebsocket, 2000);
	}
}

function handleLogout(reason) {
	console.warn("Logging out: " + reason);
	localStorage.removeItem("session_token");
	// Optionally, show a message to the user
	alert("You have been logged out. " + reason);
	setTimeout(function() {
		window.location.href = "/login.html";
	}, 1000);
}

function sendMessage(message) {
	if (connected && ws && ws.readyState === WebSocket.OPEN) {
		ws.send(JSON.stringify(message));
	} else {
		console.warn("WebSocket is not connected. Unable to send message: ", message);
	}
}

function sendCommand(command, args = {}) {
	const message = {
		type: "input_command",
		command: command,
		args: args
	};

	sendMessage(message);
}

// Start the WebSocket connection when the page loads
window.addEventListener("load", function() {
	wsConnect();
});