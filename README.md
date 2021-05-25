# Build your own “AirTag” like crowd souring BLE Tracker.
  It's an end-to-end encrypted beacon scanning system which is suitable in crowd souring tracking. The project demoestrate the ability using Raspberry Pi as Accessory (or Tag) and an Laptop running Ubuntu as Scanning Devices and Owner Devices. Would be applied to ESP32 and Android/iOS devices as next step. 

## How it works:
  * Phase 1: initialize the tag
    - Owner Device pair and connect with the tag. 
    - -> Owner Device generate 512 Bit RSA key pair 
    - -> Owner device keep the private key safely and transfer the public key to the tag with GATT profile. 
    - -> Tag to enter beacon mode and keep broadcasting 512 bit public key in a power effecient way
  * Phase 2: Lost and Searching
    - Any scanner (all devices that running scanning service) to receive the beacon would take the public key and encrypt current location. Then send the encrypted location infomation along with the public key to server. 
  * Phase 3: Found
    - Owner device would query the server with the stored public key and decrypted the content using securely kept private key, finally got the location of the tag without leaking any information of the scanner. 
	
## How to use:  
  * Accessory - Raspeberry Pi 4B or Zero/W (with bluetooth) running official image
      > sudo python3 accessory.py
  * Owner Device - Linux based system
      > pip3 install cryptography  
    - Generate RSA key pair
      > python3 key_management.py 
    - Scan and connect with tag with sepecific UUID defined in BLE_helper.py. Once connected, public key would be transfer to the tag. And the tag would restart BLE advertisement and start to broadcase the public key. 
      > python3 device.py owner-set
    - Crowd sourcing scanner to scan beacons. Once the beacon found, information would be encrypted and upload to server. You can use the service URL enclosed directly or build your own server. 
      > python3 device.py scanner
    - Query and decrypted to find the location.
      > python3 device.py owner-find
		
## Next step:
  1. Support ESP32 and other low cost BLE module. 
  2. Open source 	Tag hardware design
  3. Open source iOS and Android application.
  4. Support ECC based SM2 asymmetric encryption
