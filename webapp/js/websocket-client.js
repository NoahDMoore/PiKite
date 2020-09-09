var photo = " "
var runtime = " "
var altitude = " "
var connected = false

document.getElementById("connect-button").addEventListener("click", connect);

function connect() {
	if (connected == false) {
		connected = true;
		document.getElementById('connect-button').setAttribute('disabled', 'true');
		document.getElementById('connect-dialog').style.display = "none";
		document.getElementById('connect-spinner').style.display = "block";
		startWebsocket();
	}
}

function startWebsocket() {

	var ws = new WebSocket("ws://" + "192.168.50.174" + ":1234/");

	ws.onerror = function (event) {
		alert("Something went wrong. Connection failed.");
		connected = false;
		document.getElementById("photo").style.cursor = "pointer";

	}

	ws.onmessage = function (event) {
		var obj = JSON.parse(event.data);


		if (obj.hasOwnProperty("alert")) {
			if (obj.hasOwnProperty("request")) {
				if (obj["request"] == "password") {
					document.getElementById('connect-spinner').style.display = "none";
					document.getElementById('password-dialog').style.display = "block";
					document.getElementById('password-alert').innerHTML = obj["alert"];

					document.getElementById("password-input").addEventListener("keyup", function(event) {
					    event.preventDefault();
					    if (event.keyCode === 13) {
					        document.getElementById("password-button").click();
					    }
					});

					document.getElementById("password-button").addEventListener("click", function(){
						password = document.getElementById('password-input').value
						ws.send(password);
					});
				}
			} else if (obj.hasOwnProperty("handshake")) {
				if (obj['handshake'] == "success") {
					document.getElementById('password-dialog').style.display = "none";
					document.getElementById('success-dialog').style.display = "block";
					document.getElementById('success-alert').innerHTML = obj["alert"];
					document.getElementById('connection-dialog').style.opacity = "0";
					setTimeout(function(){
						document.getElementById('connection-dialog').style.display = "none";
					}, 3100);
				} else {
					document.getElementById('password-dialog').style.display = "none";
					document.getElementById('failure-dialog').style.display = "block";
					document.getElementById('failure-alert').innerHTML = obj["alert"];
				}
			} else {
				var snackbarContainer = document.querySelector('#demo-toast-example');
				var data = {message: obj['alert']};
				snackbarContainer.MaterialSnackbar.showSnackbar(data);
			}
		}

		if (obj.hasOwnProperty("photo")) {
			if (obj["photo"] != photo) {
				document.getElementById("photo").src = "photos/" + obj["photo"];
				photo = obj["photo"];
			}
		}

		if (obj.hasOwnProperty("runtime")) {
			if (obj["runtime"] != runtime) {
				document.getElementById("runtime").innerHTML = "Runtime:</br>" + obj["runtime"];
				runtime = obj["runtime"];
			}
		}
		if (obj.hasOwnProperty("altitude")) {
			if (obj["altitude"] != altitude) {
				document.getElementById("altitude").innerHTML = "Altitude:</br>" + obj["altitude"] + "'";
				altitude = obj["altitude"];
			}
		}
	};
}
