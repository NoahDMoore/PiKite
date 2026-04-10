var connected = false

function wsConnect() {
	if (connected == false) {
		connected = true;
		startWebsocket();
	}
}

function startWebsocket() {
    websocket_url = "ws://" + location.host + "/ws";
	var ws = new WebSocket(websocket_url);

	ws.onmessage = function (event) {
		var obj = JSON.parse(event.data);
        if (obj.hasOwnProperty("alert")) {
            alert(obj["alert"]);
        }
	};
}