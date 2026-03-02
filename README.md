
# Yen Bai Buddhist Village Ewelink lights control project

## Summary

This repo automatically manage the street lights in the village depending on weather conditions and the sunrise/sunset times. This repo implements a python CLI application that calls the Ewelink API and the open-meteo.com API for weather forecast and sunrise/sunset times.

## Ewelink API

### Ewelink API v2 fiasco and authentication hurdles

Note that when googling, the first result will lead you to https://github.com/skydiver/ewelink-api which is a Javascript library, however it has not been updated in 3 years and there has been some recent changes to Ewelink's API causing it to stop working (switching from normal user/pass to Oauth authentication. Supposedly it is no longer supported and there is another more recent and supposedly official way of using the Ewelink API: https://github.com/nocmt/eWeLinkOAuthLoginDemo?tab=readme-ov-file (which uses the OAuth 2.0 auth flow). See this comment in one of ewelink-api's issues for context: https://github.com/skydiver/ewelink-api/issues/221#issuecomment-1684931386

It seems that it is still possible to log in via user/pass along with an APP_ID and APP_SECRET that is obtainable via registering as a developer from Ewelink's (official?) developer portal: https://dev.ewelink.cc/#/settings.

Being more familiar with python and wanting to fully manage the codebase, I decided to write a simple implementation to directly call Ewelink's API using python instead (of the skydiver/ewelink-api JS code). The main python packages used are requests and click (for building a CLI app).

### Workaround
Right now, I am using some random person's APP ID and SECRET: [^1]

APP_ID: Uw83EKZFxdif7XFXEsrpduz5YyjP7nTl
APP_SECRET: mXLOjea0woSMvK9gw7Fjsy7YlFO4iSu6

I have also signed up for a developer account in Ewelink's dev portal page and [have created an application entry there](https://dev.ewelink.cc/#/console) so I do have my own APP_ID and APP_SECRET in order to use their API. However, it seems that the APP_ID I created has a "Standard" app role, and there are limitations to which API endpoints it can call. The `/v2/user/login` endpoint which still uses the username/password and bypasses Ewelink API's new Oauth2 flow is not accessible by this standard app role. I think the reason for this is due to the explanation given here: https://github.com/skydiver/ewelink-api/issues/220#issuecomment-1676739532. To quote:

> Regarding authorization issues, accounts created by individual developers can only be redirected to the authorization page for login. So it cannot directly request the login interface to obtain a Token...

The `Uw83EKZ...` APP ID seems to have access to call the "old" login endpoint`/v2/user/login` so I will for now keep using this APP ID until it no longer works :D . 

There was mention that this poses some security risks to use someone else's APP ID and SECRET, however I cannot see how it is a security risk in that there is still no way someone could control the Village's devices through my Ewelink account without knowing my account's username and password, even if they have knowledge of the APP ID and SECRET. And if they did obtain my Ewelink username and password, they would be able to control the devices anyway through the regular Ewelink Android app. So the attack vector is unclear here. See this discussion on the security risk: https://github.com/skydiver/ewelink-api/issues/221#issuecomment-1683429664

### Oauth2 login

The Oauth2 flow seems like a pain to setup, plus the fact that it requires the user to login to Ewelink's account via a web browser before being redirected back to a redirect URL of our choice with an access token (see https://coolkit-technologies.github.io/eWeLink-API/#/en/OAuth2.0). This makes it hard to use the Ewelink in a CLI-only app in headless systems (no GUI). Perhaps there is some magic to do all of this without ever needing to open a web browser, but I won't go that route until it is necessary. There is a demo github repo on how to setup this Oauth2 flow using nodejs: https://github.com/nocmt/eWeLinkOAuthLoginDemo

https://stackoverflow.com/questions/21058183/whats-to-stop-malicious-code-from-spoofing-the-origin-header-to-exploit-cors
https://portswigger.net/web-security/cors/access-control-allow-origin

## Open-Meteo

This is a free weather service offering registration-free access to their API, which has a limit of 10000 calls per day for the basic plan. This is more than enough for our needs.

## Links

Ewelinks developer docs: https://coolkit-technologies.github.io/eWeLink-API/#/en/DeveloperGuideV2?id=become-a-developer
open-meteo API Docs example page (Location set to Hop Minh ward already): https://open-meteo.com/en/docs#latitude=21.7&longitude=104.861&hourly=temperature_2m,precipitation_probability,precipitation,cloud_cover&daily=sunrise,sunset&timezone=auto&forecast_days=1 

open-meteo API pointing to Hop Minh ward and displaying all needed information (precipitation chance, cloud cover, sunset/sunrise times): https://api.open-meteo.com/v1/forecast?latitude=21.7229&longitude=104.9113&hourly=temperature_2m,precipitation_probability,precipitation,cloud_cover&daily=sunrise,sunset&timezone=Asia%2FBangkok&forecast_days=1


[^1]: See the following references to this APP ID being used as a workaround for many people:
- https://github.com/skydiver/ewelink-api/issues/212#issuecomment-1485629138
- https://github.com:limsongyu/ewelink-api
- https://github.com/skydiver/ewelink-api/issues/221#issue-1850227686
- https://github.com/skydiver/ewelink-api/issues/220#issuecomment-1672670091
