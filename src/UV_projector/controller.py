import warnings
import RPi.GPIO as GPIO
import time
import enum
import math
import numpy as np

class Mode(enum.IntEnum):
    STANDBY = 0xFF,
    EXTERNALPRINT = 0x06,
    TESTPATTERN = 0x01
    
class DLPC1438:
    """
    Representation of the DLPC1438 DMD controller. Communication between the user board (raspberry
    pi) and the DLPC1438 are handled will this class. It is assumed the image data is
    being transmitted over the parallel video interface of the DCLP1438, and that this
    image data is being stored in frame buffer 0 (/dev/fb0). 
    """

    addr = 0x1B  # i2c address

    def __init__(self, i2c_bus, PROJ_ON_PIN, HOST_IRQ_pin):
        """
        Checks if the DCLP1438 is running and ready for i2c communication, and if not, will 
        start the DLPC1438 with the PROJ_ON gpio signal.
        """
        print("Intialising the DLPC1438...")

        self.PROJ_ON = PROJ_ON_PIN
        self.HOST_IRQ = HOST_IRQ_pin

        # Configure the pins
        GPIO.setup(self.PROJ_ON, GPIO.OUT)  
        GPIO.setup(self.HOST_IRQ, GPIO.IN)  

        self.i2c = i2c_bus

        # Reset the DCLP1438
        GPIO.output(self.PROJ_ON, GPIO.LOW)    
        time.sleep(1)
            
        # send the PROJ_ON signal and wait for the HOST_IRQ signal to go high, signalling the DLPC1438
        # is ready to go
        GPIO.output(self.PROJ_ON, GPIO.HIGH)
        ref_time = time.time()
        while not GPIO.input(self.HOST_IRQ):
            time.sleep(0.001)

        print(f"DLPC1438 is signalling it is ready for use, {time.time()-ref_time} seconds after PROJ_ON went high.")

        # wait until we can see the DLPC1438 on i2c bus
        while True:
            time.sleep(0.05)
            try:
                # Try reading from DCLP1438. Will give OSError if not found (yet)
                self.i2c.read_byte(self.addr)
                print(f"DCLP1438 is ready for i2c communication")

                time.sleep(0.3)  # we need some extra wait time after this TODO: figure out why

                break  # break out of while loop and continue
            except OSError:
                #print("waiting for i2c...")
                # DLPC1438 i2c not ready yet. Ignore and try again
                pass

        return
        
    def __i2c_read(self, register, length):
        """Read I2C information from DCLP1438 at given register, expecting a certain number of bytes
        of data.
        
        This function exists primarily to keep a code more readable."""
        return self.i2c.read_i2c_block_data(self.addr,register,length)
    
    def __i2c_write(self, register, data):
        """Write I2C information from DCLP1438 at given register, sending a list of bytes specified
        in 'data'.
        
        This function exists primarily to keep a code more readable."""
        return self.i2c.write_i2c_block_data(self.addr,register,data)

    def switch_mode(self, new_mode):
        """
        Switch between DLPC1438 operational modes.

        Note that the input of the function must be an Enum of the Mode class.
        """
        # check that the new mode is actually a valid enum entry 
        if isinstance(new_mode, Mode):  
            print(f"> Switching DLPC1438 mode to {new_mode.name}\t (currently in {self.__i2c_read(0x06,1)[0]})")

            self.__i2c_write(0x05, [new_mode])  # send the new mode setting

            time.sleep(0.4)  # need some time to switch between modes

            # check that the mode switch was successful
            if new_mode != Mode.STANDBY: 
                queried_mode = self.__i2c_read(0x06,1)[0]
                assert queried_mode == new_mode.value, f"Was unable to switch the DLPC 1438 to MODE:{new_mode}"
            else:  # STANDBY sometimes gives a different status code. If so you can handle it here.
                # TODO: figure out why this gives different code sometimes
                queried_mode = self.__i2c_read(0x06,1)[0]
                print(f"Standby status: {queried_mode}")
                assert queried_mode == new_mode.value, f"Was unable to switch the DLPC 1438 to MODE:{new_mode}"

            # if we switched to EXTERNAL_PRINT mode, we will want to wait for 
            # SYS_READY to go high before doing anything else. eViewTek board does not
            # expose pin over the FPC, so we we will just wait for 1s.
            if queried_mode == Mode.EXTERNALPRINT:
                time.sleep(1)

        else:
            raise Exception("Invalid DLPC1438 mode provided. Use the Enum 'Mode', rather than the hex value.")
    
    def configure_external_print(self, LED_PWM): 
        """
        Apply various settings applicable to the EXTERNAL_PRINT mode of the DLPC1438.

        This function will configure multiple registers. Note that switching to STANDBY mode will
        likely reset some of these values, so it is suggested to call this before switching
        to EXTERNAL_PRINT mode.
        """

        print(f"\nConfiguring the DLPC1438 for external print mode with LED PWM at {LED_PWM/1023*100}%")

        assert isinstance(LED_PWM, int), "LED_PWM must be a 10-bit integer"
        assert 0 <= LED_PWM < 1024, "LED_PWM must be 10-bit (i.e. in range [0, 1023])"

        # write external print confugration (0xA8)
        # we choose a linear transfer function (byte 1) and select led 3 (byte 2)
        self.__i2c_write(0xA8, [0x00, 0x04])  # set gamma and led
        print(f"External print settings: {self.__i2c_read(0xA9,2)}")

        # Write LED PWM current (0x54)
        # Set PWM value for LED 3 (default anycubic is (0xB4, 0x00))
        print(LED_PWM.to_bytes(2, byteorder = 'big'))
        PWM_data = [0x00, 0x00, 0x00, 0x00] + list(LED_PWM.to_bytes(2, byteorder = 'little'))
        self.__i2c_write(0x54, PWM_data)  
        print(f"LED settings: {[hex(val) for val in self.__i2c_read(0x55,6)]}") 

        # set image orientation
        self.__i2c_write(0x14, [0x00])
        

    def expose_pattern(self, exposed_frames, dark_frames=5):
        """
        Start exposure of the data on parallel video interface with a specified number of exposed frames.

        The exposure time is set in number of frames. I assume this is in the framerate
        set by the parallel interface. 

        Dark frames are there to minimise any switching artifacts. I havent tested well enough
        if it makes a difference. It looks smooth enough when playing back video, so it
        seems safe to run with dark_frames=0
        """
        # Ideally we would check SYS_READY signal here
        assert isinstance(dark_frames, int), "dark_frames must be a 16-bit integer"
        assert 0 <= dark_frames < 65536, "dark_frames must be 16-bit (i.e. in range [0, 65535])"

        if exposed_frames > 0:
            assert isinstance(exposed_frames, int), "exposed_frames must be a 16-bit integer"
            assert 0 <= exposed_frames < 65536, "exposed_frames must be 16-bit (i.e. in range [0, 65535])"

            # start exposure of current buffer for the duration specifed in exposure time
            print(f"> Starting UV exposure (for {exposed_frames} frames / {exposed_frames/60:.2f}sec)!")
            frame_data = [0x00] + \
                list(dark_frames.to_bytes(2, byteorder = 'little')) + \
                list(exposed_frames.to_bytes(2, byteorder = 'little'))
            self.__i2c_write(0xC1,frame_data )
            # the value above never seem to be read back correctly if you read over I2C. 

        elif exposed_frames == -1:
            # start exposure of current buffer for infinite duration with 5 dark frames to let video data stabilise)
            print("> Starting UV exposure (Infinite Duration)!")
            self.__i2c_write(0xC1, [0x00]
                              + list(dark_frames.to_bytes(2, byteorder = 'little'))
                              + [0xFF, 0xFF])  
            # the value above never seem to be read back correctly if you read over I2C. Also on anyubic board.'

        else:
            raise Exception("Invalid exposure time value provided. Value must be positive or -1.")

        time.sleep(0.02) # TODO: optimise delay time; now this is just quick empirical test

    def stop_exposure(self):
        """
        Stop the UV exposure in external print mode
        
        This command is used to stop exposure in case the projector is set to 'indefinite' mode
        in the expose_pattern() command. This then allows the controller (e.g. raspberry pi) to
        control the start and stop time, rather than the DLPC1438. Can be useful in dynamic
        exposure settings, where the total exposure time is not known in advance.

        An alternative way to turn off the projector in indefinite projection mode is to turn
        it to standby mode, but that is not always the desired method.
        """

        print("Stopping UV exposure immediately!")
        self.__i2c_write(0xC1, [0x01, 0x00, 0x00, 0x00, 0x00])  

        time.sleep(0.1) # TODO: optimise delay time; now this is just quick empirical test

