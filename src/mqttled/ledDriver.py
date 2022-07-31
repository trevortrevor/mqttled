from os.path import join

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

class LedDriver():
    def __init__(self, light_id:str, triggers):
        self.path = join("/sys/class/leds/", light_id)
        self.triggers = triggers
        
        with open(join(self.path, "brightness")) as f:
            self.brightness = int(f.read().rstrip())
        with open(join(self.path, "trigger")) as f:
            self.current_trigger, self.triggers = parse_trigger(f.read().rstrip(), self.triggers)

        self.state = "OFF" if self.current_trigger == 'none' else "ON"


    def turn_on(self, on_mode="default-on"):
        with open(join(self.path, "trigger"), "w") as f:
            f.write(on_mode)
        self.state = 'ON'


    def turn_off(self):
        with open(join(self.path, "trigger"), "w") as f:
            f.write("none")
        self.state = 'OFF'
        self.set_brightness(0, store=False)


    def set_brightness(self, val:int, store=True):
        with open(join(self.path, "brightness"), "w") as f:
            f.write(str(val))
        if store:
            self.brightness = val
