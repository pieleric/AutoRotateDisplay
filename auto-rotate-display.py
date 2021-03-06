#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Daemon which reads the position of the laptop and change the display rotation so that it's always horizontal.
"""

import os
import re
import time
import sys
import subprocess
#import xrandr

def run_shell_cmd(cmd):
    """runs a shell commands and returns the string generated by the command."""
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    out = p.stdout.read().strip()
    return out  #This is the stdout from the shell command

# TODO if the font rendering is using subpixel rendering, we should also rotate the order (eg: RGB -> vRGB)

class AutoRotate:
    """The main class for autorotation"""

    # TODO it would be better to directly read xrandr info (via the xrandr module or pyrandr) (but it doesn't support xrandr 1.2 rotation yet)
    # Read the current rotation 
    #screen = xrandr.get_current_screen()
    #output = screen.get_output_by_name(output)
    #sys.stderr.write("rot %d" % screen.get_current_rotation());
    output = ""
    current_rotation = "normal"
    def xrandr_init(self):
        """Find which output to rotate, and get its current rotation"""
        # Cache the xrandr info as we'll use it several times
        XRANDR_INFO = run_shell_cmd('xrandr --verbose')

        # Find the display we are interested to move (= the laptop panel)
        POSSIBLE_OUTPUT = ["LVDS", "LVDS1"]
        for out in POSSIBLE_OUTPUT:
            match = re.search("^" + out +  r" connected .* \(.*\) (?P<rotation>.*) \(",
                             XRANDR_INFO,
                             re.MULTILINE
                             )
            if match:
                self.output = out
                self.current_rotation = match.group("rotation")
                print out + "=" + self.current_rotation
                break

    # rotation String left / right / inverted / normal
    def rotate_screen(self, rotation):
        """Rotates the screen with the given rotation."""
        return subprocess.call(["xrandr", "--output", self.output, "--rotate", rotation])

    XINPUT_DEVICES = []
    def xinput_init(self):
        """Find the X input devices which should be rotated. (touchpads and touchscreens)"""
        XINPUT_INFO = run_shell_cmd('xinput --list')
        for line in XINPUT_INFO.splitlines():
            # We look for the line countaining the name of the device
            match = re.match(r'"(?P<name>.*)"\W+id', line)
            if match:
                input_name = match.group("name")
            # We look for the second line, countaining the type
            input_type_line = re.match(r"\W+Type is (?P<type>\w+)", line)
            if input_type_line:
                input_type = input_type_line.group("type")
                # only the devices attached to the laptop
                if (input_type == "TOUCHPAD") or (input_type == "TOUCHSCREEN"):
                    #print "found " + input_name
                    self.XINPUT_DEVICES.append(input_name)

    # rotation String left / right / inverted / normal
    def rotate_xinput(self, rotation):
        """Rotates the axes of the X input devices"""
        # XXX for now it works only with evdev-handled devices
        if rotation == "normal" :
            evdev_swap = 0
            evdev_inv_x = 0
            evdev_inv_y = 0
        elif rotation == "inverted" :
            evdev_swap = 0
            evdev_inv_x = 1
            evdev_inv_y = 1
        elif rotation == "left" :
            evdev_swap = 1
            evdev_inv_x = 0
            evdev_inv_y = 1
        elif rotation == "right" :
            evdev_swap = 1
            evdev_inv_x = 1
            evdev_inv_y = 0
        else:
            raise
            
        for dev in self.XINPUT_DEVICES:
            # TODO: generate X calls directly
        #    print (["xinput", "set-int-prop", dev, "Evdev Axes Swap", "8", str(evdev_swap)])
        #    print (["xinput", "set-int-prop", dev, "Evdev Axis Inversion", "8", evdev_inv_x, evdev_inv_y])
            subprocess.call(["xinput", "set-int-prop", dev, "Evdev Axes Swap",
                             "8", str(evdev_swap)])
            return subprocess.call(["xinput", "set-int-prop", dev, "Evdev Axis Inversion",
                             "8", str(evdev_inv_x), str(evdev_inv_y)])


    # From Pavel Herrmann
    # (Will need more work to be integrated)
    wacom_devices = []
    def wacom_init(self):
        """Initialise the wacom devices info"""
        #wacom_list = ["stylus"]
        # TODO Should use "xsetwacom list" to determine if there is a device to rotate
        #WACOM_NAME = ""
        #if wacom_list[0]:
        #	current_wacomrotation=run_shell_cmd('xsetwacom get '+ wacom_list[0] +' Rotate')

    # n number 1 / 2 / 3 / 0
    def rotate_wacom(self, rotation): 
        """Rotates the tablet/touchscreen with the given rotation."""
        if rotation == "normal" :
            rot = "0"
        elif rotation == "inverted" :
            rot = "3"
        elif rotation == "left" :
            rot = "2"
        elif rotation == "right" :
            rot = "1"
        else:
            raise

        for dev in self.wacom_devices:
            return subprocess.call(["xsetwacom", "set", dev, "Rotate", rot])

    #def sgn(number):
    #    return (number/abs(number))

    # rotation String left / right / inverted / normal
    def rotate(self, rotation): 
        """Rotates the screen and inputs with the given rotation."""
        if self.current_rotation != rotation :
            ret = self.rotate_screen(rotation)
            #print rotation
            if ret == 0:
                self.rotate_xinput(rotation)
                self.current_rotation = rotation

    def update_pos(self, x, y, z):
        """Parse the current position and rotate if necessary."""
        #print x, y, z 
        if x < (-2 * self.MAX_SENSOR/3) :
            # physical screen rotated 90° ccw
            self.rotate("right")
        elif x > (2 * self.MAX_SENSOR/3) :
            # physical screen rotated 90° cw
            self.rotate("left")
        elif z < 0 :
            # physical screen rotated 180° cw
            self.rotate("inverted")
        elif (x < self.MAX_SENSOR / 3 ) and (x > (-self.MAX_SENSOR / 3)):
            # normal
            self.rotate("normal")

    accel_dev = ""
    MAX_SENSOR = 1024
    def accel_init(self):
        """Find the accelerometer device, and initialises the maximum value."""
        # To use the joystick instead, see pygame.joystick.Joystick
        POSSIBLE_DEV = ["lis3lv02d", "hdaps", "applesmc"]
        # TODO: add a fallback to look just for any device with a "position" file which has a (.*) content
        for dev in POSSIBLE_DEV:
            filename = "/sys/devices/platform/" + dev + "/position"
            if os.path.isfile(filename):
                self.accel_dev = filename

        if self.accel_dev == "":
            sys.stderr.write("Error: no accelerometer found.\n")
            sys.exit(1)

        # TODO: associate the MAX to the type of sensor
        # lis3lv02d can have 1024 or 127 depending on the exact HW
        self.MAX_SENSOR = 1024

    def daemon(self):
        """Reads the accelerometer's value regularly and rotates as needed"""
        while True:
            time.sleep(1)
            try:
                f = open(self.accel_dev, 'r')
                line = f.readline()
            except:
                print "Unexpected error while reading the position: ", sys.exc_info()[0]
                time.sleep(10)
                raise
            axes = re.split("\(|,|\)", line)
            # length is +2 because of empty string at the beginning and \n
            if len(axes) == 4:
                self.update_pos(int(axes[1]), int(axes[2]))
            elif len(axes) == 5:
                self.update_pos(int(axes[1]), int(axes[2]), int(axes[3]))

    def __init__(self):
        self.accel_init()
        self.wacom_init()
        self.xinput_init()
        self.xrandr_init()
    

if __name__ == "__main__":
    ar = AutoRotate()
    ar.daemon()

# vim:shiftwidth=4:expandtab:spelllang=en_gb:spell:         
