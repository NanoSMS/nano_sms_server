# Nano SMS

NanoSMS combines SMS and the Nano network by providing a SMS interface to a server backed Nano wallet. Users ‘text’ the wallet with commands, these are parsed, passed to the server which then manages the wallet and sends SMS replies. Users are identified by their telephone number as a unique number, these are directly linked to private keys held on the server. By identifying by telephone number its also possible to use telephone numbers as a transaction address therefore hiding the complex nano address system.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

What things you need to install the software and how to install them

```
Python3
Twilio Account
Server
```

### Installing

Install dependencies

```
bin/pip install -r requirements.txt
```

And activate

```
source bin/activate
```

You should see:

```
Running on http://127.0.0.1:5000/
```

## Configure webhook URL Twilio

For Twilio to know where to look, you need to configure your Twilio phone number to call your webhook URL whenever a new message comes in.

	1. Log into Twilio.com and go to the Console's Numbers page.
	2. Click on your SMS-enabled phone number.
	3. Find the Messaging section. The default “CONFIGURE WITH” is what you’ll need: "Webhooks/TwiML".
	4. In the “A MESSAGE COMES IN” section, select "Webhook" and paste in the URL you want to use.

Save your changes. 

### Using the application

From any mobile phone send SMS to registered twilio number. The following commands are supported

```
commands
register
details
address
history
balance
send
claim
trust
recover
```

### Register with NanoSMS

Send "register" to NanoSMS number, you should recieve the following message:

```
Welcome to NanoSMS, your address: xrb_addressvalue
Code: 1234
```

### Send Nano with NanoSMS

To send nano you need funds in your account, an authentication code, and a destination number. The following example shows how to send Nano.

Command sent:
```
send 50 +15417543010 1234
```

Reply:
```
Sent!
Code: 1002
```

Send commands always follow the format
```
Send (amount) (phone number) (authentication code)
```

### Claim free Nanos with NanoSMS

Send "claim" to NanoSMS number, you should recieve some free Nano to get you started:

```
Claim Success (10 nanos)

AD1: check out localnanos to exchange nano
AD2: Cerveza Polar 6 for 1Nano at JeffMart, 424 Caracas
Code: 1234
```

## Built With

* [Twilio](https://www.twilio.com/docs/sms/quickstart/python) - The SMS API
* [Flask](http://flask.pocoo.org/) - Microframework


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

