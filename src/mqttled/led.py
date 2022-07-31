import json
import logging
import re
from os.path import join
from paho.mqtt.client import Client, MQTTMessage

from mqttled.ledDriver import LedDriver


class Led:
    def __init__(self, led_id, controller):
        self.client = controller.mqtt
        self.id = re.sub('[^A-Za-z0-9]+', '-', led_id)
        self.led = LedDriver(led_id, controller.triggers_config)
        
        self.topic        = join(controller.topic, led_id)
        self.commandTopic = join(self.topic, "set")
        self.stateTopic   = join(self.topic, "state")

        self.client.message_callback_add(self.commandTopic, self.on_message)

        logging.info(f"LED: {self.id} subscribed to {self.commandTopic}")
        self.discoveryPayload = json.dumps({
            "availability_topic"    : join(controller.topic, "connection"),
            "state_topic"           : self.stateTopic,
            "unique_id"             : controller.model + "_" + self.id,
            "brightness"            : True,
            "brightness_scale"      : 254,
            "command_topic"         : self.commandTopic,
            "effect_list"           : self.led.triggers,
            "effect"                : True,
            "name"                  : self.id,
            "schema"                : "json",
            "device"                : controller.device,
            "json_attributes_topic" : self.stateTopic
        })
            
    def json_state(self):
        return json.dumps(
            {
                "state": self.led.state,
                "brightness": self.led.brightness,
                "trigger": self.led.current_trigger 
            }
        )   

    def on_message(self, client:Client, userdata, msg:MQTTMessage):
        payload:dict[str] = json.loads(msg.payload)
        logging.debug(f"{msg.topic}: {payload}")
        
        if "state" in payload.keys():
            state = payload['state']
        else:
            logging.error("Unknown command message")    
            return
        
        effect    = payload.get("effect", "default-on")
        brightness = payload.get('brightness', self.led.brightness)

        if state == "OFF" or effect == "none":
            self.led.turn_off()
        elif state == 'ON':
            self.led.turn_on(effect)
            self.led.set_brightness(brightness)
        else:
            logging.warning(f'Unknown state: {state}')
        

        self.publish_update()
            
    def publish_update(self):
        self.client.publish(self.stateTopic,self.json_state(), retain=True)


       
if __name__ == '__main__':
    exit()
