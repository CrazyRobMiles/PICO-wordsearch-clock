# Building the Circuit

![Circuit diagram of the clock](../images/Alarm%20Circuit_bb.png)

The diagram shows the circuit for the clock. If you are not building the alarm clock you only need these:

* Raspberry PI PICO 2 W
* 16x16 led panel with 10mm led spacing. 
* DuPont cables. The prototypes were constructed by using short DuPont male-to-male cables which were soldered into the switch connections onto the LED panel. the other male end of the cables were soldered into the PICO directly. One special cable was created which split the VBUS power connection so that the leds and the DFPlayer could be powered. 

## Alarm Clock

![Image of the inside of the clock showing connections](../images/clock%20internals.jpg)

You can make a version of the clock which will sound an alarm at a set time during the day. The alarm sounds are stored on a Micro-SD card inside the clock and played by a DFPlayer device controlled by the PICO. The alarm clock uses four buttons to set the alarm. You need these extra components:

* DFPlayer - search for "DFPlayer Mini mp3" 
* Micro-SD card – between 4Gbytes and 16Gbytes work well
* Four non-latching push buttons which fit in a 13mm diameter hole
* 40mm speaker with mounting holes spaced at 32.5mm

## Design Changes

You can modify the FreeCAD program that creates the case if you wish to use differently sized components.  You can modify the **settings.json** file for the device if you want to use different pin assignments in your circuit.

[Resources Home](../README.md)