#!/usr/bin/env python3

from asyncio import open_connection
import os
import json
import paho.mqtt.client as mqtt
import re
import netifaces as ni
import encodings.idna
import logging
from uci import Uci
import sys
import signal

class ledHost(object):
    def __init__(self, config):
        self._config = config
        self._triggersconfig = self._config['triggers']['triggers']
        self._model = self._config['mqtt'].get('model', os.uname().nodename)
        u = Uci()    
        self._mqtt = mqtt.Client()
        self.running = False

        try:
            self._bind_if = u.get("network",self._config['mqtt']['interface'],"device")
            self._interface_ip = ni.ifaddresses(self._bind_if)[ni.AF_INET][0]['addr']
        except:
            logging.warn('Interface not found in config, binding to all')
            self._interface_ip = None       
        if self._config['mqtt'].get('username', None):
            self._mqtt.username_pw_set(self._config['mqtt']['username'],
                                       self._config['mqtt'].get('password', None))         
        if self._config['mqtt'].get('cafile', None):
            self._mqtt.tls_set(self._config['mqtt']['cafile'],
                               self._config['mqtt'].get('certfile', None),
                               self._config['mqtt'].get('keyfile', None))            
        self._topic = self._config['mqtt']['basetopic'] + "/" + self._config['mqtt']['subtopic'] + "/"
        self._discoveryTopic = self._config['mqtt']['discovery'] + "/"  
        self._mqtt.will_set(self._topic + "connection", 'offline', retain=True)
        self._mqtt.on_connect = self._on_mqtt_connect
        self._mqtt.on_disconnect = self._on_mqtt_connect
        self._mqtt.on_message = self._on_message
  
        logging.info('MQTT broker host: %s, port: %d, use tls: %s',
                     config['mqtt']['host'],
                     int(config['mqtt']['port']),
                     bool(config['mqtt'].get('cafile', None))) 
        self._device = {
            "identifiers": ["openWrtLED" + "-" + self._model],
            "name": os.uname().nodename,
            "manufacturer": "OpenWRT",
            "model": self._model, 
        } 
        if self._config['leds']['includeall'] == '1' or self._config['leds']['includeall'] == True:
            logging.debug('LEDS include all set')
            try:
                self.leds = eval(str(os.listdir("/sys/class/leds")))
            except FileNotFoundError as e:
                logging.warn('No LEDS found in /sys/class/leds')
                sys.exit()
        else:
            logging.debug('Include all not set, adding ' + str(self._config['leds']['include']))
            self.leds = self._config['leds']['include']
        self.leds = {x:_led(x, self) for x in self.leds}    
        for entry in self._config['leds']['exclude']:
            del self.leds[entry]      
        for light in self.leds.values():
            self._mqtt.message_callback_add(light.commandTopic, light.on_message)
        
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
                  
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        logging.info('Connected to MQTT broker with code %s', rc)

        lut = {mqtt.CONNACK_REFUSED_PROTOCOL_VERSION: 'incorrect protocol version',
               mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED: 'invalid client identifier',
               mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE: 'server unavailable',
               mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD: 'bad username or password',
               mqtt.CONNACK_REFUSED_NOT_AUTHORIZED: 'not authorized'}
        if rc != mqtt.CONNACK_ACCEPTED:
            logging.error('Connection refused from reason: %s', lut.get(rc, 'unknown code'))
        if rc == mqtt.CONNACK_ACCEPTED:
            logging.info('subscribed to  %s + #', self._topic)
            client.subscribe(self._topic + "#")
            client.publish(self._topic + "connection", "online", retain=True)
            self.publishDiscovery()
    def _on_mqtt_disconnect(self, client, userdata, rc):
        logging.info('Disconnect from MQTT broker with code %s', rc)
        
    def _on_message(self, client, userdata, message):
        logging.debug('mqtt_on_message %s %s', message.topic, message.payload) 
         
    def _unhandled_message(self, client, userdata, message):
        logging.info('Unhandled message: %s %s', message.topic, message.payload)
        
    def run(self):
        self._mqtt.connect_async(self._config['mqtt']['host'], int(self._config['mqtt']['port']), bind_address=self._interface_ip)
        self.running = True
        logging.info('MQTT LED Control Started')
        self._mqtt.loop_forever()
        
    def stop(self, sig=None, stack=None):
        self.running = False
        self._mqtt.publish(self._topic + "connection", "offline", retain=True)
        self._mqtt.disconnect()
        self._mqtt.loop_stop()
        try:
            logging.info('mqttled stopped by signal: ' + str(sig) + " " + stack )
        except:
            pass
        logging.info('MQTT LED Control Stopped')
        
    def publishDiscovery(self):
        for light in self.leds.values():
            self._mqtt.publish(self._discoveryTopic + "light/" + self._device['name'] + "/" + light.id + "/config", light.discoveryPayload, retain=True)
            light.publish_update()

class _led:
    def __init__(self, id, controller):
        self.client = controller._mqtt
        self.triggers = controller._triggersconfig
        self.id = re.sub('[^A-Za-z0-9]+', '-', id)
        self.path = "/sys/class/leds/" + id +"/"

        with open(self.path + "brightness") as f:
            self.brightness = int(f.read().rstrip())
        with open(self.path + "trigger") as f:
            self.current_trigger, self.triggers = self.parseTrigger(f.read().rstrip(), self.triggers)
        if self.current_trigger == 'none':
            self.state = 'OFF'
        else:
            self.state = 'ON'
        self.topic = controller._topic + id + "/"
        self.commandTopic = self.topic + "set"
        self.stateTopic = self.topic + "state"
        self.client.message_callback_add(self.commandTopic, self.on_message)
        logging.info(f"LED: {self.id} subscribed to {self.commandTopic}")
        self.discoveryPayload = json.dumps({
            "availability_topic"    : controller._topic + "connection",
            "state_topic"           : self.stateTopic,
            "unique_id"             : controller._model + "_" + self.id,
            "brightness"            : True,
            "brightness_scale"      : 254,
            "command_topic"         : self.commandTopic,
            "effect_list"           : self.triggers,
            "effect"                : True,
            "name"                  : self.id,
            "schema"                : "json",
            "device"                : controller._device,
            "json_attributes_topic" : self.stateTopic
        })
        
    def turn_on(self, on_mode="default-on"):
        with open(self.path + "trigger", "w") as f:
            f.write(on_mode)
        self.state = 'ON'
    
    def turn_off(self):
        with open(self.path + "trigger", "w") as f:
            f.write("none")
        self.state = 'OFF'
        
    def adjust_brightness(self, val=255):
        with open(self.path + "brightness", "w") as f:
            f.write(str(val))
        self.brightness = val
        
    def json_state(self):
        return json.dumps(
            {
                "state": self.state,
                "brightness": self.brightness,
                "trigger": self.current_trigger    
            }
        )    
    def on_message(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        logging.debug(f"{self.path}: {payload}")
        
        if "state" in payload.keys():
            command = payload['state']
        else:
            logging.error("Unknown command message")    
            return
        
        if "effect" in payload.keys(): 
            on_mode = payload['effect']
        else:
            logging.debug("no on_mode specified")    
            on_mode = 'default-on'
            

        if on_mode == "none":
            self.turn_off()
        elif command == 'ON':
            self.turn_on(on_mode)
        elif command == 'OFF':
            self.turn_off()
        else:
            logging.warn(f'Unknown state: {command}')

        if "brightness" in payload.keys():
            self.adjust_brightness(payload['brightness'])
        else:
            self.adjust_brightness(self.brightness)

        self.publish_update()
            
    def publish_update(self):
        self.client.publish(self.stateTopic,self.json_state(), retain=True)

    def parseTrigger(self, triggerFile, triggersConfig):
        triggers = triggerFile.split()
        retTriggers = []
        currentTrigger = ""
        for trigger in triggers:
            if trigger[0] == "[":
                currentTrigger = trigger.strip('[]')
                retTriggers.append(currentTrigger)
            if trigger in triggersConfig:
                retTriggers.append(trigger)
        return currentTrigger, retTriggers
       
if __name__ == '__main__':
    sys.exit()