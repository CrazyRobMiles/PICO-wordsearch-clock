# Alarm Sounds

The sounds for the alarm clock are stored on a MicroSD card which is fitted inside the DFPlayer. The DFPlayer does not use the filenames to access sound files, instead it uses the absolute numbers of the files on the card. When you ask it to play file 1 it will play the first file loaded onto the card, and so on. 

The first two files on the card are the alarm off (file 2) and alarm on (file 1) messages. These are played when the user toggles the alarm status. The remaining files are all different alarm sound messages. When the alarm is triggered it picks a random sound and plays that. There are two sets of alarm messages in this repository. The **tones** folder contains a set of alarm tones. The **voice** folder contains a set of alarm voice messages. 

If you make your own alarm clock you will need to copy the sound files onto an SD card, making sure that you copy the alarm off and alarm on messages first. Then copy as many of the different voice and tone files (along with your own) as you like. Once you have done this you need to tell the alarm clock the voice files you wish to use for alarms. You do this by editing settings in the **settings.json** file in the firmware folder:

```json
    "App_wordsearch_alarmclock": {
        "start_audio_track_no": 3,
        "end_audio_track_no": 20,
```

Find the settings for **App_wordsearch_alarmclock** and then set the values of **start_audio_track_no** and **end_audio_track_no** to match the number of sound files on the MicroSD card. 

If you copy the contents of the **voice** folder onto the card after the alarm off and alarm on messages, the above settings will cause the clock to pick a random voice message when the alarm goes off. If you add the **tone** sounds on the end of the card the start and end track numbers would be 21-41. If you use the range 3 to 41 you will get a mixture of tones and voice messages. 


[Resources Home](../README.md)