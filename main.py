from asyncio import open_connection
import os
import json
import paho.mqtt.client as mqtt
import re
import netifaces as ni
import encodings.idna
import yaml
with open("config.yaml", 'ro') as config:
    try:
        configuration = yaml.safe_load(config)
    except yaml.YAMLError as exc:
        print(exc)
bind_if = configuration['interface']
discovery_topic = configuration['dicovery_topic']
base_topic = configuration['base_topic']
model = configuration['model']    
interface_ip = ni.ifaddresses(bind_if)[ni.AF_INET][0]['addr']

hostidentifier = os.uname()
ha_discovery = base_topic + "_" + hostidentifier.nodename + "/"
sub_topic = hostidentifier.nodename
topic = base_topic + "/" + sub_topic + "/"

device = {
        "identifiers": ["openWrtLED" + hostidentifier.nodename],
        "name": hostidentifier.nodename,
        "manufacturer": "OpenWRT",
        "model": model, 
}

def parseTrigger(triggerfile):
    triggers = triggerfile.split()
    for i, trigger in enumerate(triggers):
        if trigger[0] == "[":
            triggers[i] = trigger.strip('[]')
            currentTrigger = trigger.strip('[]')
            break
    return currentTrigger, triggers

class led(object):
    def __init__(self, id):
        self.id = re.sub('[^A-Za-z0-9]+', '', id)
        self.path = "/sys/class/leds/" + id +"/"
        with open(self.path + "brightness") as f:
            self.brightness = f.read().rstrip()
        with open(self.path + "trigger") as f:
            self.current_trigger, self.triggers = parseTrigger(f.read().rstrip())
        if self.current_trigger == 'none':
            self.state = 'off'
        else:
            self.state = 'on'
        self.topic = topic + re.sub('[^A-Za-z0-9]+', '', id)
        self.commandTopic = self.topic + "/set"
        self.stateTopic = self.topic + "/state"
        self.discoveryPayload = json.dumps({
            "availability_topic"    : topic + "connection",
            "state_topic"           : self.stateTopic,
            "unique_id"             : hostidentifier.nodename + "_" + self.id,
            "brightness"            : True,
            "brightness_scale"      : 254,
            "color_mode"            : False,
            "command_topic"         : self.commandTopic,
            "effect_list"           : self.triggers,
            "effect"                : True,
            "name"                  : hostidentifier.nodename + " " + self.id,
            "schema"                : "json",
            "device"                : device
        })
        
    def turn_on(self, on_mode="default-on"):
        os.system('echo ' + on_mode + ' > ' + self.path + "trigger")
    
    def turn_off(self):
        os.system('echo "none" > ' + self.path + "trigger")
        
    def adjust_brightness(self, val=255):
        os.system('echo ' + str(val) + ' > ' + self.path + "brightness")
        
    def json_state(self):
        return json.dumps(self.__dict__)
    
    def on_message(self, client, userdata, msg):
        msg = json.loads(msg.payload)
        try:
            command = msg['state']
        except:
            print("Unknown command message")    
        try:
            on_mode = msg['effect']
        except KeyError:
            print("no onmode sepecified")
            on_mode = 'default-on'
        if command == 'on':
            self.turn_on(on_mode)
        elif command == 'off':
            self.turn_off()

leds = eval(str(os.listdir("/sys/class/leds")))
leds = {x:led(x) for x in leds}    
    
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("connected to mqtt")
    else:
        print("Failed to connect with rc:" + rc)
    client.subscribe(base_topic + "/#")

def unhandled_message(client, userdata, msg):
    print("Unknown message")
    print(str(msg.topic))
    print(str(msg.payload))
    
print(interface_ip)
      
client = mqtt.Client(hostidentifier.nodename)
client.on_connect = on_connect
client.username_pw_set('tom', 'wA8ru1pe')
client.connect("192.168.1.5", bind_address=str(interface_ip))
client.message_callback = unhandled_message
for light in leds.values():
    client.message_callback_add(light.commandTopic, light.on_message)
client.loop_start()   
for light in leds.values():
    client.publish(discovery_topic + ha_discovery + light.id + "/light/config", light.discoveryPayload)
    client.publish(light.stateTopic,light.json_state())
while True:
    pass
