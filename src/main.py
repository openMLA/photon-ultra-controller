import RPi.GPIO as GPIO
import time
import smbus  # I2C

from UV_projector.controller import DLPC1438, Mode

from PIL import Image

GPIO.setmode(GPIO.BCM)

HOST_IRQ = 6  # GPIO pin for HOST_IRQ
PROJ_ON = 5  # GPIO pin for PROJ_ON

i2c = smbus.SMBus(8)  # we configured our software i2c to be on bus 8

### Controlling DMD ################################################################################

# Initialise the DLPC1438
DMD = DLPC1438(i2c, PROJ_ON, HOST_IRQ)
# Configure it (NOTE: standby can clear these settings)
DMD.configure_external_print(LED_PWM=512)

# switch to right mode
DMD.switch_mode(Mode.EXTERNALPRINT)

DMD.expose_pattern(-1)  # expose for infinite duration (until we stop it)

### Writing data to framebuffer ####################################################################

# NOTE: this example still uses RGB565 framebuffer. This needs to be fixed to RBG888. On todo list.

import numpy as np
# Map the screen as Numpy array
# N.B. Numpy stores in format HEIGHT then WIDTH
# we have RGB565 format so lets load all pixel data into single 16bit uint
# and then we can edit that as we like
h, w, c = 720, 1280, 4
fb = np.memmap('/dev/fb0', dtype='uint16',mode='w+', shape=(h, w)) 

red =   0b1111100000000000
green = 0b0000011111100000
blue =  0b0000000000011111
white = 0b1111111111111111
colors = [red, green, blue, white]

# example: channel separation (red is wired to grayscale of projector)

fb[:] = [red]  
input("Press Enter to continue...")
fb[:] = green  # should be dark
input("Press Enter to continue...")
fb[:] = blue   # should be dark
input("Press Enter to continue...")

shift_red = lambda x: x << 11  # utility function

# example: increasing grayscale intensity

for i in range(32):
    fb[:300] = shift_red(31)  # max intensity
    print(bin(shift_red(i)))
    fb[300:] = shift_red(i)
    print(f'Intensity val {i}')
    time.sleep(0.3) 
    #input("Press Enter to continue...")
input("Press Enter to continue...")

# example: displaying png image

print("-- Converting image to bytes --")
print(fb.shape)
im_frame = Image.open("../media/openMLA_logo_1280x720.png")
pixeldata = np.array(im_frame).astype(np.uint16)
rescaled = pixeldata/255
rescaled = rescaled*31
print(np.unique(rescaled))
rescaled_int = rescaled.astype(np.uint16)

shiftdata = shift_red(rescaled_int)
print(shiftdata)
print(np.unique(shiftdata))

fb[:] = shiftdata
input("Press Enter to continue...")

# example: gradient (repeats)

row = np.arange(1280) % 32
grad_array = np.tile(row, (720, 1))
shiftdata = grad_array << 11
fb[:] = shiftdata
input("Press Enter to continue...")

# example: cube 

cube = np.zeros((720,1280))
cube[300:400, 300:400] = 31
cube_data = cube.astype(np.uint16)
fb[:] = (cube_data << 11)
input("Press Enter to continue...")

# turn light off
DMD.stop_exposure()  

time.sleep(0.3)
DMD.switch_mode(Mode.STANDBY)  # leave system in standby
