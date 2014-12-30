import Adafruit_CharLCD as LCD

import datetime
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
		HOST,PORT="localhost",9999
		self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self.sock.connect((HOST,PORT))
		self.lastGPS = None
		self.lastTPV = None		

	def run(self):
		while True:
			data = {'command':'get-data'}
			self.sock.sendall(json.dumps(data)+'\n')
			received=self.sock.recv(2048)
			self.lastDataSet=json.loads(received)
			if 'gps' in self.lastDataSet:
				temp= self.lastDataSet.pop('gps') ## strip out gps data if there is any and hold on to it if it's a tpv packet (as opposed to a sky packet)
				self.lastGPS = temp
				if(temp['class'] == 'TPV'):
					self.lastTPV = temp
			self.readData=True
			time.sleep(0.1)

	def incrementSLPValue(self,amount):
		HOST,PORT="localhost",9999
		sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		sock.connect((HOST,PORT))
		new_value = amount+float(self.lastDataSet['bmp_085']['set_seaLevelPressure'])
		data = {'command':'set-sea-level-pressure','value':new_value}
		sock.sendall(json.dumps(data)+'\n')
		sock.close()


dataReader = ReadDataLoop()

class RecordDataLoop(threading.Thread) :
	def __init__(self):
		super(RecordDataLoop,self).__init__()
		self.stopRequested=False
		self.intervalSeconds = 1

	def run(self):
		while True:
			data = dataReader.lastDataSet
			if dataReader.lastGPS != None:
				data['gps'] = dataReader.lastGPS
				print dataReader.lastGPS
				dataReader.lastGPS = None

			last_json = json.dumps(data)
			 
			with open(self.filename,'a') as output_file:
				output_file.write(last_json+'\n')
			time.sleep(self.intervalSeconds)
			if(self.stopRequested):
				break;
	def request_stop(self):
		self.stopRequested = True
		self.join()
	def request_start(self):
		dt=datetime.datetime.now()
		self.filename = '/home/pi/projects/vario-one/'
		self.filename += 'recorded-{year}-{month}-{day}-{hour}-{min}-{sec}'.format(year=dt.year,month=dt.month,day=dt.day,hour=dt.hour,min=dt.minute,sec=dt.second)
		self.daemon=True
		self.start()

class ScreenBase:
	def get_name(self):
		return 'base'
	def on_up(self):
		return
	def on_down(self):
		return
	def on_left(self):
		return
	def on_right(self):
		return
	def display(self):
		return

class MainScreen (ScreenBase) : 
	def get_name(self):
		return 'main'
	def display(self):
		lcd.set_color(1.0, 0.0, 1.0)
		lcd.home()
		temperature=dataReader.lastDataSet['bmp_085']['lpf_temperature']
		pressure=dataReader.lastDataSet['bmp_085']['lpf_pressure']
		altitude=dataReader.lastDataSet['bmp_085']['lpf_altitude']
		altitude_rate = dataReader.lastDataSet['bmp_085']['lpf_altitude_rate'];
		lcd.message('{0:0.1f}c {2:0.1f}m \n{1:0.0f}Pa {3:0.1f}m/s'.format(temperature,pressure,altitude,altitude_rate))

class DataRecorderScreen (ScreenBase):
	def __init__(self):
		self.dataRecorder = None

	def get_name(self):
		return 'data_recorder'
	def on_up(self):
		if self.dataRecorder == None:
			self.dataRecorder = RecordDataLoop()
			self.dataRecorder.request_start()
	def on_down(self):
		self.dataRecorder.request_stop()
		del self.dataRecorder
		self.dataRecorder = None
	def on_left(self):
		return
	def on_right(self):
		return
	def display(self):
		lcd.set_color(1.0,0.0,0.0)
		lcd.home()
		status = 'rec' if self.dataRecorder != None else 'off '
		interval = 'x' if self.dataRecorder == None else self.dataRecorder.intervalSeconds
		lcd.message('{0} {1} '.format(status,interval))
		
class SetSLPScreen (ScreenBase): 
	def get_name(self):
		return 'set_slp'
	def on_up(self):
		dataReader.incrementSLPValue(50.0)
	def on_down(self):
		dataReader.incrementSLPValue(-50.0)
	def display(self):
		global set_slp_value
		lcd.set_color(0.0,0.0,1.0)
		lcd.home()
		altitude=dataReader.lastDataSet['bmp_085']['lpf_altitude']
		setSLPValue=dataReader.lastDataSet['bmp_085']['set_seaLevelPressure']
		lcd.message('set slp: {0: 0.0f}Pa\n{1:0.0f}m'.format(setSLPValue,altitude))
		
class GPSScreen (ScreenBase):
	def get_name(self):
		return 'gps'
	def display(self):
		lcd.set_color(0.0,1.0,0.0)
		lcd.home()
		
		data = dataReader.lastTPV
		if(data != None):
			kmh = data['speed']*3.6
			lat = '{0:0.4f}'.format(data['lat'])  if 'lat' in data else 'lat'
			lon = '{0:0.4f}'.format(data['lon']) if 'lon' in data else 'lon'
			speed = '{0:2.1f}'.format(kmh) if 'speed' in data else 'xx.x'
			alt = '{0:4.0f}'.format(data['alt']) if 'alt' in data else 'xxxx'
			heading = '{0:3.0f}'.format(data['track']) if 'track' in data else 'xxx'
		
			lcd.message('{0},{1}\n{3} {4}m {2}'.format(lat,lon,heading,speed,alt))

setSLPScreen = SetSLPScreen()
dataRecorderScreen = DataRecorderScreen()
mainScreen = MainScreen()
gpsScreen = GPSScreen()

class DisplayLoop(threading.Thread) : 

	def __init__(self):
		super(DisplayLoop,self).__init__()
		self.display_page = mainScreen.get_name()
		self.buttons = []

	def run(self):
		self.display_loop()

	def get_screen_object(self):
		if self.display_page == 'main':
			return mainScreen
		elif self.display_page == 'set_slp':
			return setSLPScreen
		elif self.display_page == 'data_recorder':
			return dataRecorderScreen
		elif self.display_page == 'gps':
			return gpsScreen
		else:
			return mainScreen

	def display_loop(self):
		while True:
			screen = self.get_screen_object()
			screen.display()
			self.process_buttons()
			time.sleep(0.025)

	def on_button(self,name):
		self.buttons.append(name);

	def process_buttons(self):
		if(len(self.buttons) > 0):
			
			process=self.buttons.pop(0)
			if(process == 'select'):
				self.on_select()
			screen = self.get_screen_object()

			if(process == 'up'):
				screen.on_up()
			elif(process == 'down'):
				screen.on_down()
			elif(process == 'left'):
				screen.on_left()
			elif(process == 'right'):
				screen.on_right()

	def on_select(self):
		if(self.display_page == 'main'):
			self.display_page = 'gps'
		elif(self.display_page == 'gps'):
			self.display_page = 'set_slp'
		elif self.display_page == 'set_slp':
			self.display_page = 'data_recorder'
		else:
			self.display_page = 'main'
		lcd.clear();

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

