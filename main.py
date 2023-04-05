####THIS FILE GENERATES ELECTRUM COMPATIBLE SEEDS AND KEYS CREATE A BACKUP BEFORE CHANGING####


from hdwallet import HDWallet
from hdwallet.utils import generate_entropy
from hdwallet.symbols import BTC as SYMBOL
from typing import Optional
import json
import requests
from os import path
from blockstream import blockexplorer
import wallet_utils
import testnet

STRENGTH: int = 256
ENTROPY: str = generate_entropy(strength=STRENGTH)

hdwallet: HDWallet = HDWallet(symbol=SYMBOL, use_default_path=False)

hdwallet.from_entropy(
    entropy=ENTROPY, language="english", passphrase=""
)


LEGACY: int = 44

SEGWIT_P2SH: int = 49

SEGWIT_NATIVE: int = 84

running = False

print("Welcome to Threshold Wallet")
print("Checking for config file")

#Instantiate an empty dict, We'll load our wallets into this variable
wallets = {}
#Check to see if we have a proper wallet file
config = path.isfile(".config.json") and path.getsize(".config.json") > 0
#If a wallet file is present, load it into memory
if config:
    wallet_file = open(".config.json", "r")
    existing_wallets = json.load(wallet_file)
    wallets.update(existing_wallets)
#If a wallet file is not present, loop until the user creates one
while not config:
    print("No config file found")
    print("Would you like to create one? Y/n")
    response = input()
    if response.lower() == "y":
        config_file = open(".config.json", "w")
        new_wallet = wallet_utils.create_wallet()
        print("Please name your wallet")
        name = input()
        wallets[name] = new_wallet
        config_file.write(json.dumps(wallets))
        config_file.close()
        config = True
#Ask the user if they'd like to run in interactive mode
print("Would you like to run the wallet in interactive mode? Y/n")
resp = input()
#If user says yes, begin runtime loop
if resp.lower() == "y":
    running = True
#Retrieve the total balance
print("Fetching balance")
total_balance = wallet_utils.gettotalbalance(wallets)
print("Total Balance", total_balance)
#Runtime loop...Let the user choose what to do, and then restart the loop
while running:
    print("What would you like to do?")
    print("1 Generate Addresses")
    print("2 Check Address balances")
    print("3 Testnet Wallet")
    print("4 Restore Wallet")
    print("5 Generate child wallets")
    print("6 Run Tests")
    print("7 Quit")
    resp = int(input())
    #Generate a wallet
    if resp == 1:
        print("Generating addresses")
        print("Please choose a name for your new wallet")
        name = input()
        new_wallet = wallet_utils.create_wallet()
        wallets[name] = new_wallet
        print(wallets)
        config_file = open(".config.json", "w")
        config_file.write(json.dumps(wallets))
        config_file.close()
    #Fetch balances/UTXOS through API
    elif resp == 2:
        print("Wallets")
        sum = 0
        #create an addresses list
        addresses = []
        for wallet in wallets.values():
            #add addresses from the parent wallet to the addresses list
            for address in wallet["addresses"].values():
                addresses.append(address)
            #check for child wallets
            if "children" in wallet.keys():
                print("child wallets detected")
                #add child wallets to the addresses list
                for child_wallet in wallet["children"]:
                    for address in child_wallet.values():
                        addresses.append(address)
            else:
                print("No child wallets detected")
            #print each address and its balance
            for address in addresses:
                balance = wallet_utils.getbalance(address)
                sum += balance
                print(address, balance, "BTC")
        #print the total balance
        print("Total balance", sum, "BTC")
    #Create a testnet wallet
    elif resp == 3:
        print("Generate a testnet wallet")
        test_wallet = testnet.create_testnet_wallet()
        #Currently, testnet addresses are not saved to the wallet file
        print(test_wallet)
    #Restore a wallet from seed phrase
    elif resp == 4:
        print("Fetching Wallet Info")
        print("Please enter your private key or seed phrase:")
        key = input()
        wallet = wallet_utils.restore_wallet(key)
        print("Please give your wallet a name")
        name = input()
        wallets[name] = wallet
        #Save the wallet file
        config_file = open(".config.json", "w")
        config_file.write(json.dumps(wallets))
        config_file.close()
    #Generate Child Wallets
    elif resp == 5:
        print("How many children?")
        amount = int(input())
        print("Please select a network")
        print("1 Mainnet")
        print("2 Testnet")
        network = int(input())
        #check if we are on testnet
        if network == 2:
            testnet: bool = True
        else:
            testnet: bool = False
        #generate the user's chosen amount of children
        for wallet in wallets.values():
            wallet["children"] = wallet_utils.generate_children(wallet, amount, testnet)
        print("Your new child wallets:")
        #Display the new wallets to the user and save them to the wallet file
        for wallet in wallets.values():            
            print(wallet["children"])
        config_file = open(".config.json", "w")
        config_file.write(json.dumps(wallets))
        config_file.close()
    #Run the tests
    elif resp == 6:
        testnet.runtests()
    #Terminate the program
    elif resp == 7:
        print("Terminating Program")
        running = False
    else:
        print("Please select a valid choice")

