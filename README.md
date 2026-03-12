# PICO Wordsearch Clock

A Raspberry Pi PICO powered clock that shows the time on a 16x16 character wordsearch

![TWo wordsearch clocks, one black on white and the other white on black](/resources/images/clocks.jpg)

There are two versions of the clock. One is an alarm clock. The same software works with both versions.

## Installing the software

**These instructions assume that you are familiar with MicroPython development for the Raspberry Pi PICO.**

The software is in the **firmware-PICO** folder. Install MicroPython on your device and then copy all the files in the **firmware-PICO** folder onto your device. You can use the Thonny program or Visual Studio Code with the Raspberry Pi plugin to do this. 

The best way to deploy the software is to use the Raspberry Pi Pico plugin for Visual Studio Code. Install the plugin and then open the **firmware-PICO** folder with Visual Studio Code **not** this repository. Plug the target PICO W into your computer, right click on any file in the file explorer and select **Upload Project to Pico** from the context menu that appears. Now you can configure the Wi-Fi. 

## Configuring the Wi-Fi

Once you have installed the software you will need to configure the Wi-Fi connection for your clock. The clock uses Wi-Fi to get the date and time. The configuration for Wi-Fi is in the **settings.json** file in the firmware folder. Use Thonny or Visual Studio Code 

```json
    "wifi": {
        "dependencies": [],
        "wifipwd1": "",
        "enabled": true,
        "retry_interval_ms": 30000,
        "wifissid1": ""
    },
```
You need to set values for **wifipwd1** and **wifissid1**. Save the file back to the device after you have edited it. Now, when your clock starts it will connect to your Wi-Fi and start displaying the time. 

### **IMPORTANT NOTE**

Your Wi-Fi settings are held in clear text inside the clock. Anyone who gains access to the clock could plug it into their computer and read the Wi-Fi settings out of it. It is good practice to create a "guest" Wi-Fi account for embedded devices so that anyone getting the credentials does not get access to all the devices on your home network. 

## Using the alarm clock

### Getting started
Plug in the clock and it should fetch the time from the internet start showing it. This will  take a few seconds to do this. The clock will not display the time until it has established a Wi-Fi connection. 

### Adjusting Brightness

Use the white buttons to adjust the brightness. One button makes the clock brighter and the other makes it darker. 

### Adjusting the alarm time

Press and hold the red button to set the alarm hour. Use the white buttons to adjust the hour value. Note that this is a 24-hour clock setting. Times after mid-day will be plus 12. In other words 2:00pm will be 14:00 hours. 

Press and hold the blue button to set the alarm minute. Use the white buttons to adjust the minute value. 

If you hold down a white button it will automatically step through the values for you. 

### Turning the alarm on and off

Press the red and blue buttons to turn the alarm on and off. The display will show yellow for off and red for the alarm on. 

### Alarm sound

If the alarm is enabled it will trigger at the set time. Press any button to cancel the alarm. 

### Alarm demonstration

To see a demonstration of the alarm display and sound, press both white buttons together. If the alarm is disabled you will hear one demo. 

# Building a clock of your own

You can find out how to build your own clock in the resources folder [here](/resources/README.md).

Have Fun!

[Rob Miles](https://www.robmiles.com/)
