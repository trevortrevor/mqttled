import json
import logging
import re
from os.path import join
from paho.mqtt.client import Client, MQTTMessage

def parse_trigger(triggerFile, triggersConfig):
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

class Led:
    def __init__(self, id, controller):
        self.client = controller.mqtt
        self.triggers = controller.triggers_config
        self.id = re.sub('[^A-Za-z0-9]+', '-', id)
        self.path = join("/sys/class/leds/", id)

        with open(join(self.path, "brightness")) as f:
            self.brightness = int(f.read().rstrip())
        with open(join(self.path, "trigger")) as f:
            self.current_trigger, self.triggers = parse_trigger(f.read().rstrip(), self.triggers)
        
        self.state = "OFF" if self.current_trigger == 'none' else "ON"
        
        self.topic        = join(controller.topic, id)
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
            "effect_list"           : self.triggers,
            "effect"                : True,
            "name"                  : self.id,
            "schema"                : "json",
            "device"                : controller.device,
            "json_attributes_topic" : self.stateTopic
        })
        
    def turn_on(self, on_mode="default-on"):
        with open(join(self.path, "trigger"), "w") as f:
            f.write(on_mode)
        self.state = 'ON'
    
    def turn_off(self):
        with open(join(self.path, "trigger"), "w") as f:
            f.write("none")
        self.state = 'OFF'
        self.adjust_brightness(0, store=False)
        
    def adjust_brightness(self, val:int, store=True):
        with open(join(self.path, "brightness"), "w") as f:
            f.write(str(val))
        if store:
            self.brightness = val
        
    def json_state(self):
        return json.dumps(
            {
                "state": self.state,
                "brightness": self.brightness,
                "trigger": self.current_trigger 
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
        brightness = payload.get('brightness', self.brightness)

        if state == "OFF" or effect == "none":
            self.turn_off()
        elif state == 'ON':
            self.turn_on(effect)
            self.adjust_brightness(brightness)
        else:
            logging.warn(f'Unknown state: {state}')
        

        self.publish_update()
            
    def publish_update(self):
        self.client.publish(self.stateTopic,self.json_state(), retain=True)


       
if __name__ == '__main__':
    exit()