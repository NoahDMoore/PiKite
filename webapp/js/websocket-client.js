var photo = " "
var runtime = " "
var altitude = " "
var program_state = "menu"
var start_time = 0
var runtime = 0
var previous_runtime = -1
var connected = false

document.getElementById("connect-button").addEventListener("click", connect);
document.getElementById("retry-button").addEventListener("click", connect);

function connect() {
	if (connected == false) {
		document.getElementById('connect-button').setAttribute('disabled', 'true');
		document.getElementById('connect-dialog').style.display = "none";
		document.getElementById('failure-dialog').style.display = "none";
		document.getElementById('connect-spinner').style.display = "block";
		startWebsocket();
	}
}

function startWebsocket() {

	var ws = new WebSocket("ws://" + location.host + ":1234/");

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
					connected = true;
					document.getElementById('password-dialog').style.display = "none";
					document.getElementById('success-dialog').style.display = "block";
					document.getElementById('success-alert').innerHTML = obj["alert"];
					document.getElementById('connection-dialog').style.opacity = "0";

					setTimeout(function(){
						document.getElementById('connection-dialog').style.display = "none";
					}, 3100);
				} else {
					connected = false
					document.getElementById('password-dialog').style.display = "none";
					document.getElementById('failure-dialog').style.display = "block";
					document.getElementById('failure-alert').innerHTML = obj["alert"];
				}
			} else if (obj.hasOwnProperty("program_state")) {
				program_state = obj["program_state"];
			} else {
				var snackbarContainer = document.querySelector('#demo-toast-example');
				var data = {message: obj['alert']};
				snackbarContainer.MaterialSnackbar.showSnackbar(data);
			}
		}

		if (obj.hasOwnProperty("start_time")) {
			start_time = obj["start_time"];
			setInterval(function(){
				runtime = parseInt(new Date().getTime() / 1000) - start_time;
				runtime_string = parseInt(runtime/60).toString() + ":" + (runtime % 60).toString();
				document.getElementById("runtime").innerHTML =  runtime_string;
			}, 1000);
		}

		if (connected == true) {
			if (obj.hasOwnProperty("photo")) {
				if (obj["photo"] != photo) {
					//PiKite saves photos to ~/pikite/output/photos, so you needs an Apache alias to reach it.
					if (obj["photo"] == "placeholder.png") {
						document.getElementById("pikite-image").src = "images/" + obj["photo"];
					} else {
						document.getElementById("pikite-image").src = "photos/" + obj["photo"];
					}
					photo = obj["photo"];
				}
			}

			if (obj.hasOwnProperty("altitude")) {
				if (obj["altitude"] != altitude) {
					document.getElementById("altitude").innerHTML = obj["altitude"] + "'";
					altitude = obj["altitude"];
				}
			}
		}
	};
}
