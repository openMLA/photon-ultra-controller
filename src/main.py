import RPi.GPIO as GPIO
import time
import smbus  # I2C
from PIL import Image

from UV_projector.controller import DLPC1438, Mode

GPIO.setmode(GPIO.BCM)

HOST_IRQ = 6  # GPIO pin for HOST_IRQ
PROJ_ON = 5  # GPIO pin for PROJ_ON

i2c = smbus.SMBus(8)  # we configured our software i2c to be on bus 8

### Controlling DMD ################################################################################

# Initialise the DLPC1438
DMD = DLPC1438(i2c, PROJ_ON, HOST_IRQ)
# Configure it (NOTE: Mode.STANDBY can clear these settings, so call it again after standby)
DMD.configure_external_print(LED_PWM=1023)

# switch to right mode
DMD.switch_mode(Mode.EXTERNALPRINT)

DMD.expose_pattern(-1)  # expose for infinite duration (until we stop it)

### Writing data to framebuffer ####################################################################

import numpy as np

# Map the screen as Numpy array
# the framebuffer is XR24 (BGRX) - https://www.linuxtv.org/downloads/v4l-dvb-apis-new/userspace-api/v4l/pixfmt-rgb.html
# (you can check this with `kmsprint`)

# in XR24, byte3 corresponds to the RED channel and since we have our raspberry pi DPI
# pins wired to the red channel, we need to write to those bytes with our code.

h, w, c = 720, 1280, 4
fb = np.memmap('/dev/fb0', dtype='uint8',mode='w+', shape=(h, w, c)) 
 
# fb.shape = (720,1280,4)
# we first zero the framebuffer (otherwise you can get an image of the terminal :P)
fb[:,:, 0] = 0 
fb[:,:, 1] = 0 
fb[:,:, 2] = 0 

print(">> Example: primaries (RGB, only blue matters)") ############################################

# blue  # should be dark
fb[:,:, 0] = 255 
fb[:,:, 1] = 0 
fb[:,:, 2] = 0 

input("Press Enter to continue...")
# green  # should be dark
fb[:,:, 0] = 0 
fb[:,:, 1] = 255 
fb[:,:, 2] = 0 
input("Press Enter to continue...")
#fb[:] = red   # THIS SHOULD result in full brightness
fb[:,:, 0] = 0 
fb[:,:, 1] = 0 
fb[:,:, 2] = 255 
input("Press Enter to continue...")

print(">> Example: ramping grayscale") #############################################################

for i in range(255):
    print(f'Intensity val {i}')
    fb[:,:, 2] = i 
    time.sleep(0.1) 
input("Press Enter to continue...")

print(">> Example: displaying a png image") ########################################################

print("-- Converting image to bytes --")
print(fb.shape)
im_frame = Image.open("../media/openMLA_logo_1280x720.png")
pixeldata = np.array(im_frame)

fb[:,:,2] = pixeldata
input("Press Enter to continue...")

print(">> Example: repeating grayscale gradient (1px per step)") ###################################

row = np.arange(1280) % 255
grad_array = np.tile(row, (720, 1))
fb[:,:,2] = grad_array
input("Press Enter to continue...")

print(">> Example: A cube. Yeah, thrilling.") ######################################################

cube = np.zeros((720,1280))
cube[300:400, 300:400] = 100
fb[:,:,2] = cube
input("Press Enter to continue...")

# turn light off
DMD.stop_exposure()  

time.sleep(0.3)
DMD.switch_mode(Mode.STANDBY)  # leave system in standby
