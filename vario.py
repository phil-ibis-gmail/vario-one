import Adafruit_CharLCD as LCD

import time;
import threading;
import requests;
import socket;
import json;

lcd = LCD.Adafruit_CharLCDPlate()

class ReadDataLoop(threading.Thread) :
	def __init__(self):
		super(ReadDataLoop,self).__init__()
		self.readData=False;
		HOST,PORT="192.168.8.101",9999
		self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self.sock.connect((HOST,PORT))
		

	def run(self):
		while True:
			data = {'command':'get-data'}
			self.sock.sendall(json.dumps(data)+'\n')
			received=self.sock.recv(2048)
			self.lastDataSet=json.loads(received)
			self.readData=True
			time.sleep(0.1)

	def incrementSLPValue(self,amount):
		HOST,PORT="192.168.8.101",9999
		sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		sock.connect((HOST,PORT))
		new_value = amount+float(self.lastDataSet['bmp_085']['set_seaLevelPressure'])
		data = {'command':'set-sea-level-pressure','value':new_value}
		sock.sendall(json.dumps(data)+'\n')
		sock.close()


dataReader = ReadDataLoop()


class DisplayLoop(threading.Thread) : 

	def __init__(self):
		super(DisplayLoop,self).__init__()
		self.display_page = 'main'
		self.buttons = []

	def run(self):
		self.display_loop()

	def display_loop(self):
		while True:
			if(self.display_page == 'main'):
				self.display_main()
			elif(self.display_page == 'set_slp'):
				self.display_set_slp()
			else:
				self.display_main()
			self.process_buttons()
			time.sleep(0.025)

		
	def display_main(self):
		lcd.set_color(1.0, 0.0, 1.0)
		lcd.home()
		temperature=dataReader.lastDataSet['bmp_085']['lpf_temperature']
		pressure=dataReader.lastDataSet['bmp_085']['lpf_pressure']
		altitude=dataReader.lastDataSet['bmp_085']['lpf_altitude']
		altitude_rate = dataReader.lastDataSet['bmp_085']['lpf_altitude_rate'];
		lcd.message('{0:0.1f}c {2:0.1f}m \n{1:0.0f}Pa {3:0.1f}m/s'.format(temperature,pressure,altitude,altitude_rate))

	def display_set_slp(self):
		global set_slp_value
		lcd.set_color(0.0,0.0,1.0)
		lcd.home()
		altitude=dataReader.lastDataSet['bmp_085']['lpf_altitude']
		setSLPValue=dataReader.lastDataSet['bmp_085']['set_seaLevelPressure']
		lcd.message('set slp: {0: 0.0f}Pa\n{1:0.0f}m'.format(setSLPValue,altitude))
	
	def on_button(self,name):
		self.buttons.append(name);

	def process_buttons(self):
		if(len(self.buttons) > 0):
			process=self.buttons.pop(0)
			if(process == 'select'):
				self.on_select()
			elif(process == 'up'):
				self.on_up()
			elif(process == 'down'):
				self.on_down()

	def on_select(self):
		if(self.display_page == 'main'):
			self.display_page = 'set_slp'
		else:
			self.display_page = 'main';
		lcd.clear();

	def on_up(self):
		if(self.display_page == 'set_slp'):
			dataReader.incrementSLPValue(50.0)
		
	def on_down(self):
		if(self.display_page == 'set_slp'):
			dataReader.incrementSLPValue(-50.0)

display = DisplayLoop();
		
def onSelect():
	display.on_button('select')

def onLeft():
	display.on_button('left')

def onRight():
	display.on_button('right')

def onDown(): 
	display.on_button('down')

def onUp():
	display.on_button('up')

dataReader.daemon=True;
dataReader.start();

while(dataReader.readData == False):
	time.sleep(0.1);

display.daemon=True;
display.start();

# Make list of button value, text, and backlight color.
buttons = [ [LCD.SELECT, 'Select', (1,1,1),False,onSelect],
            [LCD.LEFT,   'Left'  , (1,0,0),False,onLeft],
            [LCD.UP,     'Up'    , (0,0,1),False,onUp],
            [LCD.DOWN,   'Down'  , (0,1,0),False,onDown],
            [LCD.RIGHT,  'Right' , (1,0,1),False,onRight] ]

while True:
	for button in buttons:
		if lcd.is_pressed(button[0]) and button[3] == False:
			button[3]=True
			button[4]();
		elif not lcd.is_pressed(button[0]) and button[3] == True:
			button[3]=False

