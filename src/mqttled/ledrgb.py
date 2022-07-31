import json
import logging
from os.path import join
import re

from mqttled.ledDriver import LedDriver

class LedRGB:
    def __init__(self, name:str, r_id:str, g_id:str, b_id:str, controller):
        logging.info("Initializing RGB LED")
        self.client = controller.mqtt
        self.triggers = controller.triggers_config
        self.id = re.sub('[^A-Za-z0-9]+', '-', name)

        self.leds = [LedDriver(r_id, controller.triggers_config), LedDriver(g_id, controller.triggers_config), LedDriver(b_id, controller.triggers_config)]

        self.topic        = join(controller.topic, name)
        self.commandTopic = join(self.topic, "set")
        self.stateTopic   = join(self.topic, "state")
        
        self.client.message_callback_add(self.commandTopic, self.on_message)
        
        self.current_trigger = self.leds[0].current_trigger
        self.brightness = 255
        
        logging.info(f"LED: {self.id} subscribed to {self.commandTopic}")
        self.discoveryPayload = json.dumps({
            "availability_topic"    : join(controller.topic, "connection"),
            "state_topic"           : self.stateTopic,
            "unique_id"             : controller.model + "_" + self.id,
            "brightness"            : True,
            "brightness_scale"      : 254,
            "color_mode"            : True,
            "supported_color_modes" : ["rgb"],
            "command_topic"         : self.commandTopic,
            "effect_list"           : self.triggers,
            "effect"                : True,
            "name"                  : self.id,
            "schema"                : "json",
            "device"                : controller.device,
            "json_attributes_topic" : self.stateTopic
        })
        
    def turn_on(self, on_mode="default-on"):
        for led in self.leds:
            led.turn_on(on_mode)
        self.current_trigger = on_mode
    
    def turn_off(self):
        for led in self.leds:
            led.turn_off()
        
    def set_brightness(self, val:int, store=True):
        for led in self.leds:
            led.set_brightness(val, store)
        if store:
            self.brightness = val

    def set_color(self, r:int, g:int, b:int):
        self.leds[0].set_brightness(self.scale(r), True)
        self.leds[1].set_brightness(self.scale(g), True)
        self.leds[2].set_brightness(self.scale(b), True)
        
    def json_state(self):
        return json.dumps(
            {
                "state": 'ON' if any([led.state == "ON" for led in self.leds]) else 'OFF',
                "brightness": self.brightness,
                "trigger": self.current_trigger,
                "color_mode": "rgb",
                "color": self.get_colors()
            }
        )   

    def on_message(self, client, userdata, msg):
        payload:dict[str] = json.loads(msg.payload)
        logging.debug(f"{msg.topic}: {payload}")
        
        if "state" in payload.keys():
            state = payload['state']
        else:
            logging.error("Unknown command message")    
            return
        
        effect = payload.get("effect", "default-on")
        

        if state == "OFF" or effect == "none":
            self.turn_off()
        elif state == 'ON':
            self.turn_on(effect)
            color = payload.get("color", self.get_colors()).values()
            self.brightness = payload.get('brightness', self.brightness)
            self.set_color(*color)
        else:
            logging.warning(f'Unknown state: {state}')
        

        self.publish_update()
            
    def publish_update(self):
        self.client.publish(self.stateTopic,self.json_state(), retain=True)

    def scale(self, value:int):
        return round(float(value) * self.scale_factor)
    
    def unscale(self, value:int):
        return round(float(value)/self.scale_factor)

    def get_colors(self):
        return {
                    "r": self.unscale(self.leds[0].brightness),
                    "g": self.unscale(self.leds[1].brightness),
                    "b": self.unscale(self.leds[2].brightness),
                }
    
    @property
    def scale_factor(self, inverse:bool=False) -> float:
        return self.brightness / 255

if __name__ == '__main__':
    exit()
