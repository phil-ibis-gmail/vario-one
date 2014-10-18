
import Adafruit_BMP.BMP085 as BMP085;
import Adafruit_CharLCD as LCD

import time;
import threading;
import requests;

sensor = BMP085.BMP085();
lcd = LCD.Adafruit_CharLCDPlate()

read_data = False;
read_temperature = 0.0;
read_pressure=0.0;
read_altitude=0.0;
set_slp_value = 101320;

class ReadDataLoop(threading.Thread) :
	def run(self):
		global read_temperature;
		global read_pressure;
		global read_altitude;
		global read_data;
		global set_slp_value;
		try:
			while True:
				read_temperature = sensor.read_temperature();
				read_pressure = sensor.read_sealevel_pressure(36);
				read_altitude = sensor.read_altitude(set_slp_value);
				read_data = True;
				time.sleep(0.1)
		except Exception:
			print 'Read Data Loop exception';
			pass;


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
		global read_temperature
		global read_pressure
		global read_altitude
		lcd.set_color(1.0, 0.0, 1.0)
		lcd.home()
		lcd.message('{0:0.1f}c {2:0.1f}m\n{1:0.0f}Pa vario'.format(read_temperature,read_pressure,read_altitude))

	def display_set_slp(self):
		global set_slp_value
		lcd.set_color(0.0,0.0,1.0)
		lcd.home()
		lcd.message('set slp: {0: 0.0f}Pa\naltitude{1:0.0f}m'.format(set_slp_value,read_altitude))
	
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
		global set_slp_value
		if(self.display_page == 'set_slp'):
			set_slp_value += 50.0
		
	def on_down(self):
		global set_slp_value
		if(self.display_page == 'set_slp'):
			set_slp_value -= 50.0
	
		
class RecordLoop(threading.Thread) : 
	def run(self):
		global read_temperature;
		global read_pressure;
		global read_altitude;
		try:
			with open('errors.txt','a') as error_file:
				error_file.write("<errors>");
			self.loop()
		except KeyboardInterrupt:
			print 'Record Loop: keyboard interrupt';
			with open('errors.txt','a') as error_file:
				error_file.write("</errors>");
			pass;
	def loop(self):
		while True:
			timestamp = int(time.time());
			payload = {'temperature': read_temperature,'pressure':read_pressure,'timestamp':timestamp};
			try:
				r=requests.put('http://www.ibis-stuff.ca/apps/weather',params=payload)
				print r.text;
				print('ok: '+r.url+'\n')
			except Exception:
				with open('errors.txt','a') as error_file:
					error_file.write('<exception> '+r.url+'</exception>\n')
				pass
			time.sleep(600);

def onSelect():
	global display
	display.on_button('select')

def onLeft():
	global display
	display.on_button('left')

def onRight():
	global display
	display.on_button('right')

def onDown(): 
	global display
	display.on_button('down')

def onUp():
	global display
	display.on_button('up')

read = ReadDataLoop();
read.daemon=True;
read.start();

while(read_data == False):
	time.sleep(0.1);

display = DisplayLoop();
display.daemon=True;
display.start();

record = RecordLoop();
record.daemon=True;
record.start();

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

