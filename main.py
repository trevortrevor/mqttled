from asyncio import open_connection
from email.mime import base
import os
import json
import paho.mqtt.client as mqtt
import re
import netifaces as ni
import encodings.idna
import logging
import signal

run = True

def handler_stop_signals(signum, frame):
    global run
    run = False

signal.signal(signal.SIGINT, handler_stop_signals)
signal.signal(signal.SIGTERM, handler_stop_signals)

from uci import Uci
u = Uci()
try:
    config = u.get("mqttled")
except UciExceptionNotFound:
    logging.fatal('No config file found at /etc/config/mqttled')
    quit()
    
        
broker = config['mqtt']
ledconfig = config['leds']
triggersconfig = config['triggers']

bind_if = u.get("network",broker['interface'],"device")
discovery_topic = broker['discovery'] + "/"
base_topic = broker['basetopic']
model = broker['model']    
interface_ip = ni.ifaddresses(bind_if)[ni.AF_INET][0]['addr']
hostidentifier = os.uname()
sub_topic = broker['subtopic']
topic = base_topic + "/" + sub_topic + "/"

device = {
        "identifiers": ["openWrtLED" + hostidentifier.nodename],
        "name": hostidentifier.nodename,
        "manufacturer": "OpenWRT",
        "model": model, 
}

def parseTrigger(triggerfile):
    triggers = triggerfile.split()
    retTriggers = []
    for i, trigger in enumerate(triggers):
        if trigger[0] == "[":
            triggers[i] = trigger.strip('[]')
            currentTrigger = trigger.strip('[]')
        if trigger in triggersconfig:
            retTriggers.append(trigger)
    return currentTrigger, retTriggers

class led(object):
    def __init__(self, id):
        self.id = re.sub('[^A-Za-z0-9]+', '', id)
        self.path = "/sys/class/leds/" + id +"/"
        with open(self.path + "brightness") as f:
            self.brightness = int(f.read().rstrip())
        with open(self.path + "trigger") as f:
            self.current_trigger, self.triggers = parseTrigger(f.read().rstrip())
        if self.current_trigger == 'none':
            self.state = 'OFF'
        else:
            self.state = 'ON'
        self.topic = topic + re.sub('[^A-Za-z0-9]+', '-', id)
        self.commandTopic = self.topic + "/set"
        self.stateTopic = self.topic + "/state"
        self.discoveryPayload = json.dumps({
            "availability_topic"    : topic + "connection",
            "state_topic"           : self.stateTopic,
            "unique_id"             : hostidentifier.nodename + "_" + self.id,
            "brightness"            : True,
            "brightness_scale"      : 254,
            "command_topic"         : self.commandTopic,
            "effect_list"           : self.triggers,
            "effect"                : True,
            "name"                  : hostidentifier.nodename + " " + self.id,
            "schema"                : "json",
            "device"                : device,
            "json_attributes_topic" : self.stateTopic
        })
        
    def turn_on(self, on_mode="default-on"):
        os.system('echo ' + on_mode + ' > ' + self.path + "trigger")
        self.state = 'ON'
    
    def turn_off(self):
        os.system('echo "none" > ' + self.path + "trigger")
        self.state = 'OFF'
        
    def adjust_brightness(self, val=255):
        os.system('echo ' + str(val) + ' > ' + self.path + "brightness")
        self.brightness = val
    def json_state(self):
        return json.dumps(self.__dict__)
    
    def on_message(self, client, userdata, msg):
        msg = json.loads(msg.payload)
        try:
            command = msg['state']
        except:
            logging.error("Unknown command message")    
        try:
            on_mode = msg['effect']
        except KeyError:
            logging.info("no on_mode sepecified")
            on_mode = 'default-on'
        if on_mode == "none":
            self.turn_off()
        elif command == 'ON':
            self.turn_on(on_mode)
        elif command == 'OFF':
            self.turn_off()
        self.publish_update()
            
    def publish_update(self):
        client.publish(self.stateTopic,self.json_state())

if ledconfig['includeall'] == '1':
    leds = eval(str(os.listdir("/sys/class/leds")))
else:
    leds = ledconfig['include']
    

leds = {x:led(x) for x in leds}    
for entry in ledconfig['exclude']:
    del leds[entry]
       
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("MQTTLED has connected to the broker")
    else:
        logging.fatal("MQTTLED Failed to connect with rc:" + rc)
        run = False
    client.subscribe(base_topic + "/#")
    client.publish(base_topic + "/" + hostidentifier.nodename + "/connection", 'online', retain=True)
    

def unhandled_message(client, userdata, msg):
    logging.info("Unknown message")
    logging.info(str(msg.topic))
    logging.info(str(msg.payload))
    
logging.info("Binding MQTT Client to "+ interface_ip)
      
client = mqtt.Client(hostidentifier.nodename)
client.on_connect = on_connect
client.username_pw_set('tom', 'wA8ru1pe')
client.will_set(base_topic + "/" + hostidentifier.nodename + "/connection", 'offline', retain=True)
client.connect("192.168.1.5", bind_address=str(interface_ip))
client.message_callback = unhandled_message
for light in leds.values():
    client.message_callback_add(light.commandTopic, light.on_message)
client.loop_start()   
for light in leds.values():
    client.publish(discovery_topic + "light/" + hostidentifier.nodename + "/" + light.id + "/config", light.discoveryPayload)
    light.publish_update()
while run:
    pass

client.publish(base_topic + "/" + hostidentifier.nodename + "/connection", 'offline', retain=True)
client.disconnect()
client.loop_stop()
logging.info('MQTTLED has shutdown')