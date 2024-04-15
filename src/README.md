# Controlling the DLPC1438 with I2C and DPI

To control the eViewTek board (which in turn exposes the DCLP1438 parallel and i2c interface to use) we need to be able to output parallel RGB888 video in the right format and to send commands. 

Once you have set up the raspberry pi according to the configuration below, you can run the demo code in `main.py` and start playing around with the projector. 

If you want to play video (and timing is not super critical), you can install `mpv` and play video with `mpv <video.mp4>` (depending on orientation you may want to add `-vf=vflip`). Note that you will have to switch the projector into exposure mode (`Mode.EXTERNALPRINT`), otherwise you will not see anything. Any other means of playing video that modifies the framebuffer at `/dev/fb0` should also work.

### Configuring Raspberry pi OS Lite

>  Everything is tested on a Raspberry Pi Zero 2 running Raspbian GNU/Linux 12 (bookworm) (Lite).

To start, we need to make some changes to `/boot/config.txt`.

We need to disable the hardware I2C and SPI (for now at least). Make sure the `dtparams` for i2c, i2s, spi are all commented as below:

```shell
#Uncomment some or all of these to enable the optional hardware interfaces
#dtparam=i2c_arm=on
#dtparam=i2s=on
#dtparam=spi=on
```

Adding DPI: add the following lines: (note that in theory some of the back and front porches could be reduced according to datasheet; untested)

```
dtoverlay=vc4-kms-v3d
dtoverlay=vc4-kms-dpi-generic,hactive=1280,hfp=32,hsync=12,hbp=32
dtparam=vactive=720,vfp=6,vsync=5,vbp=6
dtparam=clock-frequency=32000000,rgb888,pixclk-invert
```

Add software I2C by adding the following lines:

```shell
# get software-defined i2c pin
dtoverlay=i2c-gpio,i2c_gpio_sda=17,i2c_gpio_scl=18,bus=8
```

If we were to leave the config.txt as above, we would lose all our GPIO, but we are not going to use the Green and Blue pixeldata pins anyway, so we would like to get those back for I2C, and other stuff. (i.e. switch them back out from their DPI `ALT` mode )

> [!NOTE]
> The method below works, but I would prefer to switch the pins out of ALT mode earlier on in the boot process. If you know how to do that, make an issue or pull request!

We can achieve this by putting the following in `/etc/rc.local`. Note that is must come before the `exit 0` line. 

```
raspi-gpio set 4-19 ip
```

Then we need to fix one final issue. If we start everything now, we notice that our framebuffer is running in RGB565 mode. Not sure why, but it is not what we want and doesn't match our DPI configuration. Luckily the fix is straightforward. We add the following to `/boot/cmdline.txt`:

```
`video=DPI-1:-32`
```
Note that the above that your DPI interface is called `DPI-1`. You can check this with `kmsprint`. It should list mode [`XR24`](https://www.linuxtv.org/downloads/v4l-dvb-apis-new/userspace-api/v4l/pixfmt-rgb.html). 

#### Checking results

Now (after rebooting) you should get something akin to the following if you run `fbset -fb /dev/fb0`

```shell
mode "1280x720"
    geometry 1280 720 1280 720 32
    timings 0 0 0 0 0 0 0
    accel true
    rgba 8/16,8/8,8/0,0/0
endmode
```

And something similar to the output below when you run `kmsprint`:

```shell
Connector 0 (32) HDMI-A-1 (disconnected)
  Encoder 0 (31) TMDS
Connector 1 (42) DPI-1 (connected)
  Encoder 1 (41) DPI
    Crtc 1 (71) 1280x720@32.02 32.000 1280/32/12/32/+ 720/6/5/6/+ 32 (32.02) P|D
      Plane 1 (61) fb-id: 294 (crtcs: 1) 0,0 1280x720 -> 0,0 1280x720 (XR24 AR24 AB24 XB24 RG16 BG16 AR15 XR15 RG24 BG24 YU16 YV16 YU24 YV24 YU12 YV12 NV12 NV21 NV16 NV61 RGB8 BGR8 XR12 AR12 XB12 AB12 BX12 BA12 RX12 RA12)
        FB 294 1280x720 XR24
```

You can also check the state of the GPIO pins with ``raspi-gpio get``. It should list something like: 

```
BANK0 (GPIO 0 to 27):
GPIO 0: level=0 alt=2 func=PCLK
GPIO 1: level=1 alt=2 func=DE
GPIO 2: level=0 alt=2 func=LCD_VSYNC
GPIO 3: level=0 alt=2 func=LCD_HSYNC
GPIO 4: level=1 func=INPUT
GPIO 5: level=1 func=INPUT
GPIO 6: level=0 func=INPUT
GPIO 7: level=1 func=INPUT
GPIO 8: level=1 func=INPUT
GPIO 9: level=0 func=INPUT
GPIO 10: level=0 func=INPUT
GPIO 11: level=0 func=INPUT
GPIO 12: level=0 func=INPUT
GPIO 13: level=0 func=INPUT
GPIO 14: level=0 func=INPUT
GPIO 15: level=1 func=INPUT
GPIO 16: level=0 func=INPUT
GPIO 17: level=1 func=INPUT
GPIO 18: level=1 func=INPUT
GPIO 19: level=0 func=INPUT
GPIO 20: level=0 alt=2 func=DPI_D16
GPIO 21: level=0 alt=2 func=DPI_D17
GPIO 22: level=0 alt=2 func=DPI_D18
GPIO 23: level=0 alt=2 func=DPI_D19
GPIO 24: level=0 alt=2 func=DPI_D20
GPIO 25: level=0 alt=2 func=DPI_D21
GPIO 26: level=0 alt=2 func=DPI_D22
GPIO 27: level=0 alt=2 func=DPI_D23
...
```



