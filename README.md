# Yen Bai Buddhist Village Rang Dong lights control project

## Summary

This repo automatically manage the street lights in the village depending on weather conditions and the sunrise/sunset times. This repo implements a python CLI application that calls the Tuya Cloud API via the tinytuya python package to command the Wifi socket and the open-meteo.com API for weather forecast and sunrise/sunset times. We are using the Rang Dong Wifi socket, which internally uses the Tuya IoT platform, hence why we are using the Tuya Cloud API.

## Tuya Cloud API

Access the developer console here: https://sg.platform.tuya.com/cloud/basic?id=p1772239736353ga5dym&toptab=related&deviceTab=all
Tinytuya python library to interface with Tuya Cloud API: https://github.com/jasonacox/tinytuya

## Open-Meteo

This is a free weather service offering registration-free access to their API, which has a limit of 10000 calls per day for the basic plan. This is more than enough for our needs.

## Links

open-meteo API pointing to Hop Minh ward and displaying all needed information (precipitation chance, cloud cover, sunset/sunrise times): https://api.open-meteo.com/v1/forecast?latitude=21.7229&longitude=104.9113&hourly=temperature_2m,precipitation_probability,precipitation,cloud_cover&daily=sunrise,sunset&timezone=Asia%2FBangkok&forecast_days=1
