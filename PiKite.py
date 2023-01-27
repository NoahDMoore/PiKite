import time
import configparser as ConfigParser
import sys
import subprocess
import os
import json
import urllib.request
import asyncio
import websockets
from picamera import PiCamera, Color
from gpiozero import Button
import xml.etree.ElementTree as ET
import board
import threading

#BME680
from busio import I2C
import adafruit_bme680

#Mini PiTFT
import digitalio
import adafruit_rgb_display.st7789 as st7789
from PIL import Image, ImageDraw, ImageFont

#PiKite Project Classes


os.chdir(os.path.dirname(sys.argv[0]))

class Menu:
	def __init__(self, xml):
		self.menu = xml
		self.state = self.menu.findall("menu_item")[0]
		self.default_state = self.state
		self.update_state()

	def __repr__(self):
		return "Menu Object with state {}".format(self.state_name)

	def __str__(self):
		return "Menu Object with state {}".format(self.state_name)

	def update_state(self):
		self.state_name = self.state.find("name").text
		self.message = self.state.find("message").text
		self.action = self.state.find("action").text
		self.previous_state = self.state.find("previous").text
		self.next_state = self.state.find("next").text

		if self.action == "return":
			self.parent = self.state.find("parent_item").text
		else:
			try:
				del self.parent
			except:
				pass

		if self.action == "options":
			self.setting = self.state.find("setting").text
			pass
		elif self.action == "selectOption":
			pass
		else:
			try:
				del self.setting
			except:
				pass

		self.print_menu()

	def do_action(self):
		if self.action == "submenu":
			self.state = self.get_menu_item(self.menu, self.state.findall("./submenu/menu_item")[0].find("name").text)
			self.update_state()
		elif self.action == "return":
			self.state = self.get_menu_item(self.menu, self.parent)
			self.update_state()
		elif self.action == "options":
			self.state = self.get_menu_item(self.state, settings_dict[self.setting], "value")
			self.update_state()
		elif self.action == "selectOption":
			update_settings(self.setting, self.state.find("value").text)
			self.state = self.get_menu_item(self.menu, self.setting, "setting")
			self.update_state()
		else:
			exec(self.action)

	def advance_state(self):
		if self.action == "selectOption":
			self.state = self.get_menu_item(self.get_menu_item(self.menu, self.setting, "setting"), self.next_state)
		else:
			self.state = self.get_menu_item(self.menu, self.next_state)

		self.update_state()

	def regress_state(self):
		if self.action == "selectOption":
			self.state = self.get_menu_item(self.get_menu_item(self.menu, self.setting, "setting"), self.previous_state)
		else:
			self.state = self.get_menu_item(self.menu, self.previous_state)

		self.update_state()

	def restart(self):
		self.state = self.default_state
		self.update_state()

	def print_menu(self):
		lcd_image, canvas = new_image()

		if any(ele in self.message for ele in image_file_types):
			lcd_image = Image.open(self.message)
		else:
			if ":" in self.message:
				if ":" in self.message:
					header = self.message.split(": ")[0] + ":"
					message = self.message.split(": ")[1]

				h = font30.getsize(self.message)[1]

				header_width = font30.getsize(header)[0]
				message_width = font30.getsize(message)[0]

				canvas.text(((IMAGE_WIDTH-header_width)/2,((IMAGE_HEIGHT-h)/2)-(h/2)), header, font=font30, fill="black")
				canvas.text(((IMAGE_WIDTH-message_width)/2,((IMAGE_HEIGHT-h)/2)+(h/2)), message, font=font30, fill="black")

			else:
				w = font30.getsize(self.message)[0]
				h = font30.getsize(self.message)[1]

				canvas.text(((IMAGE_WIDTH-w)/2,(IMAGE_HEIGHT-h)/2), self.message, font=font30, fill="black")

		lcd.image(lcd_image)

	def get_menu_item(self, xml, item, tag="name"):
		menu_item = xml.findall('.//*['+tag+'="'+item+'"]')[0]
		return menu_item

class GIF:
	def __init__(self, gif_image):
		self.image = gif_image

	def __repr__(self):
		return "GIF control for {}".format(self.image)

	def __str__(self):
		return "GIF control for {}".format(self.image)

	def __len__(self):
		return self.frame_count

	class NotInLoop(Exception): pass

	@property
	def frame_count(self):
		return self.image.n_frames - 1

	@property
	def frame(self):
		return self.image.tell()

	@frame.setter
	def frame(self, new_frame):
		if isinstance(new_frame, int):
			if new_frame <= self.frame_count and new_frame >= 0:
				self.image.seek(new_frame)
			elif new_frame < 0:
				raise ValueError("Frame must be a positive number.")
			else:
				raise ValueError("Frame does not exist. There are only {} frames in this GIF. Remember, frames start at 0.".format(self.frame_count))
		else:
			raise TypeError("Frame must be an integer")

	def display_frame(self, paste=None):
		output = self.image.convert('RGBA')
		if paste != None:
			output.paste(paste, (0,0), paste)
		lcd.image(output)

	def advance_frame(self, loop=False):
		if self.frame < self.frame_count:
			self.frame +=1
		elif self.frame == self.frame_count and loop == True:
			self.frame = 0
		else:
			raise self.NotInLoop

	def play(self, loop=False):
		self.frame = 0

		try:
			while self.frame <= self.frame_count:
				self.display_frame()
				self.advance_frame(loop)
		except self.NotInLoop:
			pass

class LoadingBar:
	def __init__(self, title):
		self.image = GIF(Image.open('loader.gif'))
		self.value = 0
		self.title = title
		self.update()

	def __repr__(self):
		return "Loading Bar, currently at {}%".format(self.percentage)

	def __str__(self):
		return "Loading Bar, currently at {}%".format(self.percentage)

	@property
	def percentage(self):
		return ((self.value / 200) * 100)

	@property
	def title(self):
		return self.title_image

	@title.setter
	def title(self, new_title):
		self.title_image = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (255,255,255,0))
		canvas = ImageDraw.Draw(self.title_image)

		w = font30.getsize(new_title)[0]
		canvas.text(((IMAGE_WIDTH-w)/2,20), new_title, font=font30, fill="black")


	def advance(self):
		if self.value < 200:
			self.value += 10
			self.update()

	def update(self):
		self.image.frame = (self.value // 10)
		self.image.display_frame(self.title)

class State:
	def __init__(self, initial_state):
		self.current_state = initial_state

	def __repr__(self):
		return self._current_state

	def __str__(self):
		return self._current_state

	def __eq__(self,comparison):
		if self._current_state == comparison:
			return True
		else:
			return False

	@property
	def current_state(self):
		return self._current_state

	@current_state.setter
	def current_state(self, new_state):
		self._current_state = new_state
		OUTGOING_MESSAGES.add(self.json_state)

	@property
	def json_state(self):
			json_data = {"program_state": self._current_state}
			json_string = json.dumps(json_data)
			return json_string

class RuntimeTimer(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self._running = False

	def stop(self):
		self._running = False

	def run(self):
		self._running = True
		self.start_time = time.time()
		self.previous_time = 0

		json_start_time = {"start_time": int(self.start_time)}
		json_string = json.dumps(json_start_time)
		OUTGOING_MESSAGES.add(json_string)

		while self._running:
			self.time = int(time.time()) - int(self.start_time)
			if self.time != self.previous_time:
				runtime_string = "{0:02d}:{1:02d}".format(int(self.time/60), int(self.time%60))
				print_one_line(runtime_string)

				self.previous_time = self.time

def new_image():
	lcd_image = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (255,255,255,255))
	canvas = ImageDraw.Draw(lcd_image)

	return lcd_image, canvas

def preloader():
	preloader = GIF(Image.open('preloader.gif'))
	preloader.play()

def get_settings():
	global settings_dict

	settings_dict = {
		"get_confirmation": "no",

		#[altitude_settings]
		"alt_reading_interval": config.get("altitude_settings", "alt_reading_interval"),

		#[camera_settings]
		"cam_take_photos": config.get("camera_settings", "cam_take_photos"),
		"cam_recording_delay": config.get("camera_settings", "cam_recording_delay"),
		"cam_rotation": config.get("camera_settings", "cam_rotation"),
		"cam_brightness": config.get("camera_settings", "cam_brightness"),
		"cam_awb_mode": config.get("camera_settings", "cam_awb_mode"),
		"cam_exposure_mode": config.get("camera_settings", "cam_exposure_mode"),

		#[photo_settings]
		"pic_interval": config.get("photo_settings", "pic_interval"),
		"pic_resolution_mode": config.get("photo_settings", "pic_resolution_mode"),
		"pic_effect": config.get("photo_settings", "pic_effect"),
		"pic_annotations": config.get("photo_settings", "pic_annotations"),

		#[video_settings]
		"vid_length": config.get("video_settings", "vid_length"),
		"vid_multiple": config.get("video_settings", "vid_multiple"),
		"vid_interval": config.get("video_settings", "vid_interval"),
		"vid_resolution_mode": config.get("video_settings", "vid_resolution_mode"),
	}

def update_settings(setting, value):
	if setting == "load_defaults":
		subprocess.call("sudo cp PiKite_Defaults.ini PiKite_Settings.ini", shell=True)
		menu.advance_state()
		menu.do_action()
	else:
		if setting[:3] == "alt":
			section = "altitude_settings"
		elif setting[:3] == "cam":
			section = "camera_settings"
		elif setting[:3] == "pic":
			section = "photo_settings"
		elif setting[:3] == "vid":
			section = "video_settings"

		config.set(section, setting, value)
		with open('PiKite_Settings.ini', 'w') as configfile:
			config.write(configfile)

	get_settings()

def display_system_info():
	program_state.current_state = "wait"

	lcd_image, canvas = new_image()

	padding = 5

	cmd = "hostname -I"
	ip = "IP: "+subprocess.check_output(cmd, shell=True).decode("utf-8").split(" \n")[0]

	cmd = "df -h | grep /dev/root | awk '{printf $3\"/\"$2}'"
	disk = subprocess.check_output(cmd, shell=True).decode("utf-8").split("G")
	disk[1] += " GB"
	disk = "Disk: "+"".join(disk)

	cmd = "iwconfig wlan0 | grep wlan0"
	network = "SSID: "+subprocess.check_output(cmd, shell=True).decode("utf-8").split("ESSID:")[1]

	try:
		response = urllib.request.urlopen('http://localhost')
		apache = "Apache: [OK]"
	except:
		apache = "Apache: [ERROR]"

	y = padding
	x = padding
	canvas.text((x, y), ip, font=font25, fill="#FF2002")
	y += font25.getsize(ip)[1] + padding
	canvas.text((x, y), disk, font=font25, fill="#C70096")
	y += font25.getsize(disk)[1] + padding
	canvas.text((x, y), network, font=font25, fill="#6BB800")
	y += font25.getsize(network)[1] + padding
	canvas.text((x, y), apache, font=font25, fill="#2121FF")

	lcd.image(lcd_image)

def shutdown_pikite():
	subprocess.call("sudo nohup shutdown -h now", shell=True)

def read_altitude(baseline=1030.0, unit="feet"):
	bme680.sea_level_pressure = baseline
	altitude = bme680.altitude

	if unit == "feet":
		altitude *= 3.28084

	altitude = str(round(altitude, 2))

	return altitude

def get_baseline_pressure():
	loader = LoadingBar("Baseline Alt:")

	baseline_pressure = 0

	i = 0
	while i < 80:
		baseline_pressure += bme680.pressure

		if i % 4 == 0:
			loader.advance()
		i += 1

		time.sleep(.1)

	baseline_pressure /= 80

	return baseline_pressure

def initialize_camera():
	camera.rotation = settings_dict["cam_rotation"]
	camera.brightness = int(settings_dict["cam_brightness"])
	camera.awb_mode = settings_dict["cam_awb_mode"]
	camera.exposure_mode = settings_dict["cam_exposure_mode"]

	type = settings_dict["cam_take_photos"]

	resolution_modes = {
		"1": {"width": 1920, "height": 1080, "fps": 30},
		"2": {"width": 2592, "height": 1944, "fps": 15},
		"5":{"width": 1296, "height": 730, "fps": 49},
		"7":{"width": 640, "height": 480, "fps": 90}
	}

	if type == "pic":
		camera.resolution = (resolution_modes[settings_dict["pic_resolution_mode"]]["width"], resolution_modes[settings_dict["pic_resolution_mode"]]["height"])
		camera.framerate = int(resolution_modes[settings_dict["pic_resolution_mode"]]["fps"])
		camera.image_effect = settings_dict["pic_effect"]

		if settings_dict["pic_annotations"] != "none":
			camera.annotate_background = Color('black')
			camera.annotate_text_size = 75
		else:
			camera.annotate_text = ''

	elif type == "vid":
		camera.resolution = (resolution_modes[settings_dict["vid_resolution_mode"]]["width"], resolution_modes[settings_dict["vid_resolution_mode"]]["height"])
		camera.framerate = int(resolution_modes[settings_dict["vid_resolution_mode"]]["fps"])

def start_focus():
	focus_thread = threading.Thread(target=focus_camera)
	focus_thread.start()

def focus_camera():
	program_state.current_state = "focusCamera"

	camera.rotation = settings_dict["cam_rotation"]
	camera.brightness = int(settings_dict["cam_brightness"])
	camera.awb_mode = settings_dict["cam_awb_mode"]
	camera.exposure_mode = settings_dict["cam_exposure_mode"]

	camera.resolution = (640, 480)
	camera.framerate = 90
	camera.image_effect = settings_dict["pic_effect"]

	print_one_line("Adjust Focus!")

	time.sleep(2)

	while program_state == "focusCamera":
		camera.capture("/home/pi/pikite/output/photos/focus.jpg")
		time.sleep(4)

	menu.restart()

	return
	

def print_one_line(message):
	lcd_image, canvas = new_image()

	w = font30.getsize(message)[0]
	h = font30.getsize(message)[1]
	canvas.text(((IMAGE_WIDTH-w)/2,(IMAGE_HEIGHT-h)/2), message, font=font30, fill="black")

	lcd.image(lcd_image)

def start_pikite():
	pikite_thread = threading.Thread(target=run_pikite)
	pikite_thread.start()

def run_pikite():
	program_state.current_state = "runningPiKite"

	baseline = get_baseline_pressure()

	initialize_camera()

	print_one_line("Ready to Launch!")
	time.sleep(2)

	folder_name = time.strftime("%m-%d-%Y-%H-%M")

	if settings_dict["cam_take_photos"] != "none":
		if not os.path.exists("/home/pi/pikite/output/photos" + folder_name):
			os.mkdir("/home/pi/pikite/output/photos/" + folder_name)

	log_file = "/home/pi/pikite/output/altitude_readings/" + folder_name + ".csv"

	with open(log_file, "a") as log:
		alt_interval = int(settings_dict["alt_reading_interval"])
		pic_interval = int(settings_dict["pic_interval"])
		cam_delay_interval = int(settings_dict["cam_recording_delay"])
		previous_alt_time = 0
		previous_pic_time = 0
		previous_send_time = 0
		timer = RuntimeTimer()
		altitude = read_altitude(baseline)
		alt_flag = False
		pic_flag = False
		socket_flag = False
		photo_location = "placeholder.png"

		if settings_dict["cam_take_photos"] == "none":
			timer.start()
			while program_state == "runningPiKite":
				if alt_flag != True:
					altitude = read_altitude(baseline)
					timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
					log.write("{0},{1}\n".format(timestamp, altitude))
					previous_alt_time = timer.time
					alt_flag = True

				if socket_flag != True:
					json_data = {"altitude": altitude}
					json_string = json.dumps(json_data)
					OUTGOING_MESSAGES.add(json_string)
					previous_send_time = timer.time
					socket_flag = True

				if timer.time > previous_alt_time + alt_interval:
					alt_flag = False

				if timer.time >= previous_send_time + 1:
					print("send")
					socket_flag = False
			timer.stop()

		elif settings_dict["cam_take_photos"] == "pic":
			timer.start()
			while program_state == "runningPiKite":
				timestamp = time.strftime("%m-%d-%Y-%H-%M-%S", time.localtime(time.time()))

				if alt_flag != True:
					altitude = read_altitude(baseline)
					log.write("{0},{1}\n".format(timestamp, altitude))
					previous_alt_time = timer.time
					alt_flag = True

				if timer.time > cam_delay_interval:
					if pic_flag != True:
						altitude = read_altitude(baseline)

						if settings_dict["pic_annotations"] == "alt":
							camera.annotate_text = "Altitude: {}'".format(altitude)
						elif settings_dict["pic_annotations"] == "time":
							camera.annotate_text = "{}".format(timestamp)
						elif settings_dict["pic_annotations"] == "alttime":
							camera.annotate_text = "Altitude: {0}'  |  {1}".format(altitude, timestamp)

						photo_location = folder_name + "/" + timestamp + ".jpg"
						camera.capture("/home/pi/pikite/output/photos/" + photo_location)
						previous_pic_time = timer.time
						pic_flag = True

				if  socket_flag != True:
					json_data = {"photo": photo_location, "altitude": altitude}
					json_string = json.dumps(json_data)
					OUTGOING_MESSAGES.add(json_string)
					previous_send_time = timer.time
					socket_flag = True

				if timer.time > previous_alt_time + alt_interval:
					alt_flag = False

				if timer.time > previous_pic_time + pic_interval:
					pic_flag = False

				if timer.time > previous_send_time + 1:
					socket_flag = False
			timer.stop()

	menu.restart()

def control_handler(input, command=""):
	if command == "":
		input = str(input.pin)
	else:
		input = "command"

	if program_state == "menu":
		if input == "GPIO17" or command == "back":
			menu.regress_state()
		elif input == "GPIO23" or command == "action":
			menu.do_action()
		elif input == "GPIO24" or command == "next":
			menu.advance_state()
		else:
			pass
	elif program_state == "wait":
		if input == "GPIO17" or command == "back":
			program_state.current_state = "menu"
			menu.print_menu()
		elif input == "GPIO23" or command == "action":
			program_state.current_state = "menu"
			menu.print_menu()
		elif input == "GPIO24" or command == "next":
			program_state.current_state = "menu"
			menu.print_menu()
		else:
			pass
	elif program_state == "runningPiKite":
		if input == "GPIO23" or command == "stopPiKite":
			program_state.current_state = "menu"
	elif program_state == "focusCamera":
		if input == "GPIO23" or command == "endFocus":
			program_state.current_state = "menu"
	else:
		pass

async def check_outgoing():
	while True:
		if OUTGOING_MESSAGES:
				message = OUTGOING_MESSAGES.pop()
				return message

async def consumer_handler(websocket):
	global INCOMING_MESSAGES
	global WEBSOCKET_CONNECTED
	while True:
		message = await websocket.recv()
		command = json.loads(message)
		if 'command' in command:
			control_handler("websocket", command['command'])
			print(command['command'])
		elif 'alert' in command:
			print(command['alert'])
			if 'handshake' in command:
				if command['handshake'] == "success":
					WEBSOCKET_CONNECTED = True
		else:
			pass

async def producer_handler(websocket):
	global OUTGOING_MESSAGES
	while True:
		if WEBSOCKET_CONNECTED == True:
			await asyncio.sleep(.5)
			if OUTGOING_MESSAGES:
				message = OUTGOING_MESSAGES.pop()
				await websocket.send(message)
		else:
			await asyncio.sleep(.5)

async def websocket_loop(loop):
	ip = subprocess.check_output("hostname -I", shell=True).decode("utf-8").split(" \n")[0]
	uri = "ws://" + ip + ":1234"

	async with websockets.connect(uri, ping_interval=None) as websocket:
		producer_task = loop.create_task(producer_handler(websocket))
		consumer_task = loop.create_task(consumer_handler(websocket))
		done, pending = await asyncio.wait(
			[consumer_task, producer_task],
			return_when=asyncio.FIRST_COMPLETED,
		)

		for task in pending:
			task.cancel()

def start_websocket_client():
	try:
		loop = asyncio.new_event_loop()
		loop.run_until_complete(websocket_loop(loop))
	except KeyboardInterrupt:
			print("\nKeyboard Interrupt: Closing The Websocket Server Before Exit")
			subprocess.call("sudo pkill -f websocket_server.py", shell=True)

def button_input():
	global back_button
	global action_button
	global next_button

	#Set Up Buttons and Callbacks
	back_button = Button(17, hold_repeat=True)
	action_button = Button(23, hold_repeat=True)
	next_button = Button(24, hold_repeat=True)

	back_button.when_pressed = control_handler
	back_button.when_held = control_handler

	action_button.when_pressed = control_handler
	action_button.when_held = control_handler

	next_button.when_pressed = control_handler
	next_button.when_held = control_handler

#Setup LCD
lcd = st7789.ST7789(
    spi=board.SPI(),
    cs=digitalio.DigitalInOut(board.CE0),
    dc=digitalio.DigitalInOut(board.D25),
    rst=None,
    baudrate=64000000,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
	rotation=270,
)

preload_thread = threading.Thread(target=preloader)
preload_thread.start()

backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

IMAGE_WIDTH = lcd.height
IMAGE_HEIGHT = lcd.width

image_file_types = ['.jpg', '.jpeg', '.gif', '.png', '.bmp', '.tiff']

font30 = ImageFont.truetype("robotobold.ttf", 30)
font25 = ImageFont.truetype("robotobold.ttf", 25)

#Import PiKite Settings
config = ConfigParser.ConfigParser()
config.read('PiKite_Settings.ini')

#Create bme680 Object
i2c = I2C(board.SCL, board.SDA)
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, debug=False)
bme680.pressure_oversample = 16

#Create PiCamera Object
camera = PiCamera()

#Import Menu XML
menu_xml = ET.parse('menu.xml').getroot()

get_settings()

p = subprocess.Popen([sys.executable, 'websocket_server.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

preload_thread.join()

OUTGOING_MESSAGES = set()
WEBSOCKET_CONNECTED = False

menu = Menu(menu_xml)

program_state = State("menu")

#Main Threads
socket_thread = threading.Thread(target=start_websocket_client)
button_thread = threading.Thread(target=button_input)

if __name__ == "__main__":
	try:
		socket_thread.start()
		button_thread.start()
	except KeyboardInterrupt:
		print("\nKeyboard Interrupt: Closing Websocket Server Before Exit")
		subprocess.call("sudo pkill -f websocket_server.py", shell=True)
