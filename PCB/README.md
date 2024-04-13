### PCB design

The design is tested with a raspberry pi zero 2, but in principle any Raspberry pi will work. The hardware pins should all be shared, but some changes in raspberry Pi OS may break stuff for newer boards. 

See [the schematic](micromirror-board-controller.pdf) for more info.

![](../media/pcb_3D_front.PNG)

![](../media/pcb_3D_back.PNG)

### Assembly

Most components are SMD, and the mouser links can be found in the basic [BOM](BOM.csv). In addition to the components of the BOM, you will also need some small wires to connect the USB data lines.

That 51-pin connector is a real pain to solder. For me going with a lower melting point solder and proper board heating made it manageable, but it's not the most enjoyable experience.



