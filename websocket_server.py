import asyncio
import websockets
import subprocess
import json
import hashlib

PIKITE_START_TIME = 0
PROGRAM_STATE = "menu"

class User:
	def __init__(self, websocket, index=0):
		self.websocket = websocket
		self.address = websocket.remote_address[0]
		self.index = index

	def __repr__(self):
		return self.name

	def __str__(self):
		return self.name

	def __contains__(self, param):
		if param == self.address:
			return True
		else:
			return False

	@property
	def name(self):
		if self.index != 0:
			return self.address + "[" + str(self.index) + "]"
		else:
			return self.address

	async def send(self, message):
		await self.websocket.send(message)

	async def recv(self):
		message = await self.websocket.recv()
		return message

	async def disconnect(self):
		await self.websocket.close()

def get_ip_address():
	ip_address = subprocess.check_output("hostname -I", shell=True).decode("utf-8").split(" \n")[0]
	return ip_address

print("Server Address: " + get_ip_address()+":1234\n")

USERS = set()

data = {}

async def register(websocket):
	index = 0
	for connection in USERS:
		if connection.address == websocket.remote_address[0]:
			index += 1
	user = User(websocket, index)
	USERS.add(user)
	return user


async def unregister(user):
    USERS.remove(user)

async def handler(websocket, path):
	global PIKITE_START_TIME
	global PROGRAM_STATE
	user = await register(websocket)

	print("{} has connected to the server. Waiting for password.".format(user))

	await asyncio.sleep(2)
	await user.send('{"alert": "Please send the password. 60s timeout.", "request": "password"}')

	try:
		if websocket.remote_address[0] != get_ip_address():
			password = await asyncio.wait_for(user.recv(), 60)
			password = hashlib.md5(password.encode()).hexdigest()
		else:
			password = "03d66e75dfc0b2a9f147dcaac2846c86"
		if password != "03d66e75dfc0b2a9f147dcaac2846c86":
			print("{} has entered an incorrect password. Connection Refused!".format(user))
			await user.send('{"alert": "Incorrect Password - Connection Refused!", "handshake": "failure"}')
			await user.disconnect()
			await unregister(user)

		else:
			print("{} has connected succesfully. Password accepted.".format(user))
			await user.send('{"alert": "Password accepted. Welcome.", "handshake": "success"}')

			if PIKITE_START_TIME != 0:
				json_start_time = {"start_time": PIKITE_START_TIME}
				json_string = json.dumps(json_start_time)
				await user.send(json_string)

			json_program_state = {"program_state": PROGRAM_STATE}
			json_string = json.dumps(json_program_state)
			await user.send(json_string)

			try:
				async for message in user.websocket:
					data = json.loads(message)
					if "start_time" in data:
						PIKITE_START_TIME = data["start_time"]
					if "program_state" in data:
							if PROGRAM_STATE == "runningPiKite":
								PIKITE_START_TIME = 0
							PROGRAM_STATE = data["program_state"]
					print(data)
					if len(USERS) > 1:
						await asyncio.wait([connection.send(message) for connection in USERS if connection != user])
			finally:
				await unregister(user)
				print("{} has disconnected from the server.".format(user))
	except asyncio.TimeoutError:
		print("{} failed to enter a password before timeout. Connection Refused.".format(user))
		await user.send('{"alert": "Password Timeout - Connection Refused!", "handshake": "timeout"}')
		await user.disconnect()
		await unregister(user)

start_server = websockets.serve(handler, get_ip_address(), 1234, ping_interval=None, ping_timeout=None)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
