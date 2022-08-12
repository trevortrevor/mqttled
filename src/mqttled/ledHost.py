#!/usr/bin/env python3


import logging
import os
import signal
from os.path import join

import netifaces as ni
import paho.mqtt.client as mqtt
from uci import Uci

from mqttled.led import Led
from mqttled.ledrgb import LedRGB

class LedHost(object):
    def __init__(self, config):
        self.config = config
        self.triggers_config = self.config['triggers']['triggers']
        self.model = self.config['mqtt'].get('model', os.uname().nodename)

        u = Uci()    
        self.mqtt = mqtt.Client()

        self.running = False

        try:
            self.bind_if = u.get("network",self.config['mqtt']['interface'],"device")
            self.interface_ip = ni.ifaddresses(self.bind_if)[ni.AF_INET][0]['addr']
        except:
            logging.warning('Interface not found in config, binding to all')
            self.interface_ip = None
        
        if self.config['mqtt'].get('username', None):
            self.mqtt.username_pw_set(
                self.config['mqtt']['username'],
                self.config['mqtt'].get('password', None)
            )         
        
        if self.config['mqtt'].get('cafile', None):
            self.mqtt.tls_set(
                self.config['mqtt']['cafile'],
                self.config['mqtt'].get('certfile', None),
                self.config['mqtt'].get('keyfile', None)
            )            
        
        self.topic          = join(self.config['mqtt']['basetopic'], self.config['mqtt']['subtopic'])
        self.discoveryTopic =      self.config['mqtt']['discovery']
        self.mqtt.will_set(join(self.topic, "connection"), 'offline', retain=True)
        self.mqtt.on_connect    = self.on_mqtt_connect
        self.mqtt.on_disconnect = self.on_mqtt_disconnect
        self.mqtt.on_message    = self.on_message
  
        logging.info('MQTT broker host: %s, port: %d, use tls: %s',
                     config['mqtt']['host'],
                     int(config['mqtt']['port']),
                     bool(config['mqtt'].get('cafile', None))) 
        self.device = {
            "identifiers": ["openWrtLED" + "-" + self.model],
            "name": os.uname().nodename,
            "manufacturer": "OpenWRT",
            "model": self.model, 
        } 
        if self.config['leds']['includeall'] == '1' or self.config['leds']['includeall'] is True:
            logging.debug('LEDS include all set')
            try:
                self.ledNames = os.listdir("/sys/class/leds")
            except FileNotFoundError:
                logging.warning('No LEDS found in /sys/class/leds')
                exit(1)
        
        else:
            logging.debug('Include all not set, adding ' + str(self.config['leds']['include']))
            self.ledNames = self.config['leds'].get('include', [])
        
        for entry in self.config['leds']['exclude']:
            try:
                self.ledNames.remove(entry) 
            except ValueError:
                logging.warning(f'{entry} not a valid led name') 

        self.leds = {x:Led(x, self) for x in self.ledNames}    

        logging.debug("RGB LED Enabled: %s", self.config["rgb"].get("enablergb", "0"))
        if self.config["rgb"].get("enablergb", '0') == '1' or self.config["rgb"].get("enablergb", False) is True:
            rgbLedNames = self.config["rgb"].keys()
            if "red" in rgbLedNames and "green" in rgbLedNames and "blue" in rgbLedNames:
                self.leds["rgb"] = LedRGB(self.config["rgb"]["name"], self.config["rgb"]["red"], self.config["rgb"]["green"], self.config["rgb"]["blue"], self)
            else:
                logging.warning("RGB LEDs not configured correctly, please check config")

        for light in self.leds.values():
            self.mqtt.message_callback_add(light.commandTopic, light.on_message)
        
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
                  
    def on_mqtt_connect(self, client, userdata, flags, rc):
        logging.info('Connected to MQTT broker with code %s', rc)

        responses = {
            mqtt.CONNACK_REFUSED_PROTOCOL_VERSION:      'incorrect protocol version',
            mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED:   'invalid client identifier',
            mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE:    'server unavailable',
            mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD: 'bad username or password',
            mqtt.CONNACK_REFUSED_NOT_AUTHORIZED:        'not authorized'
        }
        if rc == mqtt.CONNACK_ACCEPTED:
            logging.info('subscribed to  %s + #', self.topic)
            client.subscribe(join(self.topic, "#"))
            client.publish(join(self.topic, "connection"), "online", retain=True)
            self.publishDiscovery()
        else:
            logging.error('Connection refused from reason: %s', responses.get(rc, 'unknown'))

    def on_mqtt_disconnect(self, client, userdata, rc):
        logging.info('Disconnect from MQTT broker with code %s', rc)

    def on_message(self, client, userdata, message):
        logging.debug('mqtt_on_message %s %s', message.topic, message.payload) 

    def unhandled_message(self, client, userdata, message):
        logging.info('Unhandled message: %s %s', message.topic, message.payload)

    def run(self):
        self.mqtt.connect_async(self.config['mqtt']['host'], int(self.config['mqtt']['port']), bind_address=self.interface_ip)
        self.running = True
        logging.info('MQTT LED Control Started')
        self.mqtt.loop_forever()
        
    def stop(self, sig=None, stack=None):
        self.running = False
        self.mqtt.publish(join(self.topic, "connection"), "offline", retain=True)
        self.mqtt.disconnect()
        self.mqtt.loop_stop()
        try:
            logging.info('mqttled stopped by signal: ' + str(sig) + " " + stack )
        except:
            pass
        logging.info('MQTT LED Control Stopped')
        
    def publishDiscovery(self):
        for light in self.leds.values():
            self.mqtt.publish(join(self.discoveryTopic, "light", self.device['name'], light.id, "config"), light.discoveryPayload, retain=True)
            light.publish_update()

if __name__ == '__main__':
    exit()
