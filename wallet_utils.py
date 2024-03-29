from hdwallet import HDWallet, BIP44HDWallet
from hdwallet.utils import generate_entropy
from hdwallet.symbols import BTC, BTCTEST
from typing import Optional
import json
import requests
from os import path
from bitcoinutils.utils import to_satoshis
from bloxplorer import bitcoin_explorer, bitcoin_testnet_explorer

#Generate 24 word seed phrases by default
STRENGTH: int = 256
ENTROPY: str = generate_entropy(strength=STRENGTH)

#Legacy Address Derivation
LEGACY: int = 44
#Segwit P2SH Derivation
SEGWIT_P2SH: int = 49
#Segwit Native Derivation
SEGWIT_NATIVE: int = 84

#Create a new wallet from entropy
def create_wallet():
    hdwallet = HDWallet(symbol=BTC, use_default_path=False)
    hdwallet.from_entropy(entropy=ENTROPY, language="english", passphrase="")
    #Creating a new wallet will always be Segwit by Default
    #Hardened Derivation
    hdwallet.from_index(SEGWIT_NATIVE, hardened=True)
    hdwallet.from_index(0, hardened=True)
    hdwallet.from_index(0, hardened=True)
    #Non Hardened Children
    hdwallet.from_index(0)
    hdwallet.from_index(0)
    #Convert the result to a Dictionary Object
    dumps = json.dumps(hdwallet.dumps(), indent=4, ensure_ascii=False)
    loads = json.loads(dumps)
    clean_addresses(loads)
    #Create Two Empty Lists, one for Receiving Wallets and one for Change
    loads["receiving"] = []
    loads["change"] = []
    return loads

#########CREATE WALLET SET###########

#Build a full electrum wallet consisting of receiving and change addresses
def create_wallet_set(wallet: dict):
    for i in range(1, 31):
        wallet["receiving"].append(gethardaddress(wallet))
        wallet["change"].append(getchangeaddress(wallet))
    return wallet



#####################################

#Remove Unneeded Addresses from a Wallet
#Legacy should only yield legacy, Segwit should only yield segwit
def clean_addresses(wallet: dict):
    #Check for testnet derivation
    if wallet["network"] == "testnet":
        if wallet["path"][0:5] == "m/44'":
            derivation = LEGACY
        elif wallet["path"][0:5] == "m/49'":
            derivation = SEGWIT_P2SH
        else:
            derivation = SEGWIT_NATIVE
    #Default to mainnet derivation
    else:
        if wallet["path"][0:5] == "m/44'":
            derivation = LEGACY
        elif wallet["path"][0:5] == "m/49'":
            derivation = SEGWIT_P2SH
        else:
            derivation = SEGWIT_NATIVE
    #If wallet is segwit native, remove all other addresses
    if derivation == SEGWIT_NATIVE:
        wallet["addresses"].pop("p2pkh")
        wallet["addresses"].pop("p2sh")
        wallet["addresses"].pop("p2wpkh_in_p2sh")
        wallet["addresses"].pop("p2wsh")
        wallet["addresses"].pop("p2wsh_in_p2sh")
        return wallet
    #If wallet is segwit p2sh, remove all other addresses
    elif derivation == SEGWIT_P2SH:
        wallet["addresses"].pop("p2pkh")
        wallet["addresses"].pop("p2sh")
        wallet["addresses"].pop("p2wpkh")
        wallet["addresses"].pop("p2wpkh_in_p2sh")
        wallet["addresses"].pop("p2wsh_in_p2sh")
        return wallet
    #If wallet is legacy, remove all other addresses
    elif derivation == LEGACY:
        wallet["addresses"].pop("p2wpkh")
        wallet["addresses"].pop("p2wsh")
        wallet["addresses"].pop("p2sh")
        wallet["addresses"].pop("p2wpkh_in_p2sh")
        wallet["addresses"].pop("p2wsh_in_p2sh")
        return wallet
    else:
        print("Derivation not supported")
        return None


#Generates NON-HARDENED child wallets based on the root xpublic key
#This function may need reworked, it was created before we could create hardened children
def getnewaddress(xpub: str, symbol: str):
    hdwallet: HDWallet = HDWallet(symbol=symbol)
    hdwallet.from_xpublic_key(xpublic_key=xpub)
    #hdwallet.from_index(SEGWIT_NATIVE)
    #hdwallet.from_index(0)
    #hdwallet.from_index(0)

    #hdwallet.from_index(0)
    #hdwallet.from_index(1)

    dumps = json.dumps(hdwallet.dumps(), indent=4, ensure_ascii=False)
    loads = json.loads(dumps)
    return loads

#Generate a hardened receiving address
def gethardaddress(wallet: dict):
    #Check for testnet derivation
    if wallet["network"] == "testnet":
        if wallet["path"] == "m/44'/1'/0'/0/0":
            derivation = LEGACY
        elif wallet["path"] == "m/49'/1'/0'/0/0":
            derivation = SEGWIT_P2SH
        else:
            derivation = SEGWIT_NATIVE
        symbol = wallet["symbol"]
        seed_phrase = wallet["mnemonic"]
        privkey = wallet["root_xprivate_key"]
        #see how many children are in the wallet
        index = len(wallet["receiving"])
        #create the next child
        #create a wallet on the network
        hdwallet: HDWallet = HDWallet(symbol=symbol)
        #build it from the seed phrase
        hdwallet.from_mnemonic(seed_phrase)
        #follow the hardened derivation path
        hdwallet.from_index(derivation, hardened=True)
        hdwallet.from_index(1, hardened=True)
        hdwallet.from_index(0, hardened=True)
        #create the child from the final two non-hardened indices
        hdwallet.from_index(0)
        #create the next non-existent child
        hdwallet.from_index(index+1)
        dumps = json.dumps(hdwallet.dumps(), indent=4, ensure_ascii=False)
        loads = json.loads(dumps)
        #remove unnecessary addresses
        clean_addresses(loads)
        #the line below will only execute if we have some type of bug
        #we should never create children that already exist
        if loads in wallet["receiving"]:
            print("Wallet already found")
            return None
        #return wallet if we have no errors
        else:
            return loads
    else:
        #Default to Mainnet derivation
        if wallet["path"] == "m/44'/0'/0'/0/0":
            derivation = LEGACY
        elif wallet["path"] == "m/49'/0'/0'/0/0":
            derivation = SEGWIT_P2SH
        #Default to SegWit Native
        else:
            derivation = SEGWIT_NATIVE
        #Get the coin ticker
        symbol = wallet["symbol"]
        #Get the seed phrase
        seed_phrase = wallet["mnemonic"]
        #Get the root private key: ALL WALLETS ARE DERIVED FROM THIS KEY
        privkey = wallet["root_xprivate_key"]
        #Find out how many receiving wallets already exist
        index = len(wallet["receiving"])
        #create a new wallet on mainnet
        hdwallet: HDWallet = HDWallet(symbol=symbol)
        #build it from our seed phrase
        hdwallet.from_mnemonic(seed_phrase)
        #folllow the hardened derivation path
        hdwallet.from_index(derivation, hardened=True)
        hdwallet.from_index(0, hardened=True)
        hdwallet.from_index(0, hardened=True)
        #create the child from the following non-hardened indices
        hdwallet.from_index(0)
        #create the next non-existent child
        hdwallet.from_index(index+1)
        dumps = json.dumps(hdwallet.dumps(), indent=4, ensure_ascii=False)
        loads = json.loads(dumps)
        #remove unnecessary addresses
        clean_addresses(loads)
        #the line below should never execute, if it does, we have a bug
        #we should never create children that already exist
        if loads in wallet["receiving"]:
            print("Wallet already found")
            return None
        #return the wallet if we have no errors
        else:
            return loads
#Generate hardened change addresses
def getchangeaddress(wallet: dict):
    #check for testnet
    if wallet["network"] == "testnet":
        #if we are on testnet, use testnet derivation
        if wallet["path"] == "m/44'/1'/0'/0/0":
            derivation = LEGACY
        elif wallet["path"] == "m/49'/1'/0'/0/0":
            derivation = SEGWIT_P2SH
        #Default to SegWit Native
        else:
            derivation = SEGWIT_NATIVE
        #Get the coin ticker
        symbol = wallet["symbol"]
        #Get the seed phrase
        seed_phrase = wallet["mnemonic"]
        #Get the root private key, ALL WALLETS ARE DERIVED FROM THIS KEY
        privkey = wallet["root_xprivate_key"]
        #Find out how many change wallets already exist
        index = len(wallet["change"])
        #create the wallet
        hdwallet: HDWallet = HDWallet(symbol=symbol)
        #build from the seed phrase
        hdwallet.from_mnemonic(seed_phrase)
        #follow the specified derivation
        hdwallet.from_index(derivation, hardened=True)
        hdwallet.from_index(1, hardened=True)
        hdwallet.from_index(0, hardened=True)
        #build the next non-existent child
        hdwallet.from_index(1)
        hdwallet.from_index(index)
        dumps = json.dumps(hdwallet.dumps(), indent=4, ensure_ascii=False)
        loads = json.loads(dumps)
        clean_addresses(loads)
        #check to see if we already have the wallet
        if loads in wallet["change"]:
            print("Wallet already found")
            return None
        else:
        #if we have no errors, return the wallet
            return loads
    else:
        #Default to mainnet derivation scheme
        #Legacy derivation
        if wallet["path"] == "m/44'/0'/0'/0/0":
            derivation = LEGACY
        #SegWit p2sh derivation
        elif wallet["path"] == "m/49'/0'/0'/0/0":
            derivation = SEGWIT_P2SH
        #Default to native SegWit
        else:
            derivation = SEGWIT_NATIVE
        #Get the coin ticker
        symbol = wallet["symbol"]
        #Get the seed phrase
        seed_phrase = wallet["mnemonic"]
        #Get the root private key, ALL WALLETS ARE DERIVED FROM THIS KEY
        privkey = wallet["root_xprivate_key"]
        index = len(wallet["change"])
        #create the wallet
        hdwallet: HDWallet = HDWallet(symbol=symbol)
        #build it from our seed phrase
        hdwallet.from_mnemonic(seed_phrase)
        #follow the specified hardened derivation path
        hdwallet.from_index(derivation, hardened=True)
        hdwallet.from_index(0, hardened=True)
        hdwallet.from_index(0, hardened=True)
        #Create the next non-existent child
        hdwallet.from_index(1)
        hdwallet.from_index(index)
        dumps = json.dumps(hdwallet.dumps(), indent=4, ensure_ascii=False)
        loads = json.loads(dumps)
        clean_addresses(loads)
        #check if we have the wallet
        if loads in wallet["change"]:
            print("Wallet already found")
            return None
        #if we have no errors, return the wallet
        else:
            return loads

#####                                #####

#Restore a mainnet wallet
def restore_wallet(restore_keys: str):
    symbol = "BTC"
    hdwallet: HDWallet = HDWallet(symbol=symbol)
    length = len(restore_keys)
    #Restore from a private key
    if length == 64:
        hdwallet.from_private_key(private_key=restore_keys)
    #Restore from a WIF private key
    elif restore_keys[0] == "K" or restore_keys[0] == "L" or restore_keys[0] == "5":
        hdwallet.from_wif(wif=restore_keys)
    #Restore from a seed phrase
    else:
        #create the wallet
        hdwallet = HDWallet(symbol=symbol)
        #build it from the seed phrase
        hdwallet.from_mnemonic(mnemonic=restore_keys)
        #follow segwit derivation
        hdwallet.from_index(SEGWIT_NATIVE, hardened=True)
        hdwallet.from_index(0, hardened=True)
        hdwallet.from_index(0, hardened=True)
        #THIS IS THE PARENT...START AT INDEX 0
        hdwallet.from_index(0)
        hdwallet.from_index(0)
    dumps = json.dumps(hdwallet.dumps(), indent=4, ensure_ascii=False)
    loads = json.loads(dumps)
    clean_addresses(loads)
    #add space for receiving and change addresses
    loads["receiving"] = []
    loads["change"] = []
    return loads
#Retrieve a balance on mainnet or testnet
#Uses the address prefix to determine network
def getpendingbalance(address: str):
    #If we're on mainnet, use the mainnet explorer
    if address[0:3] == "bc1" or address[0] == "1" or address[0] == "3":
        data =  bitcoin_explorer.addr.get(address).data["mempool_stats"]
        #Return the balance denoted in BTC, not sats
        return (data["funded_txo_sum"] - data["spent_txo_sum"])/100_000_000
    #If we're on testnet, use the testnet explorer
    elif address[0:3] == "tb1" or address[0] =="m" or address[0] == "n" or address[0] == "2":
        data = bitcoin_testnet_explorer.addr.get(address).data["mempool_stats"]
        #Return the balance denoted in BTCTEST, not sats
        return (data["funded_txo_sum"] - data["spent_txo_sum"])/100_000_000
    else:
        #Tell the user that their address is not valid
        return "address {} not a valid BTC or BTCTEST address".format(address)

def getbalance(address: str):
    #If we're on mainnet, use the mainnet explorer
    if address[0:3] == "bc1" or address[0] == "1" or address[0] == "3":
        #return the balance denoted in BTC, not sats
        try:
            data = bitcoin_explorer.addr.get(address, timeout=(20, 20)).data["chain_stats"]
        #except (ReadTimeout, bloxplorer.exceptions.BlockStreamClientTimeout):
        except:
            print("Server Error, please check your balance again in a few minutes")
            return 0
        else:
            return (data["funded_txo_sum"] - data["spent_txo_sum"])/100_000_000

    #If we're on testnet, use the testnet explorer
    elif address[0:3] == "tb1" or address[0] =="m" or address[0] == "n" or address[0] == "2":
        #return the balance denoted in BTCTEST, not sats
        try:
            data = bitcoin_testnet_explorer.addr.get(address, timeout=(20, 20)).data["chain_stats"]
        except:
            print("Server error, please check your balance again in a few minutes")
            return 0
        else:
            return (data["funded_txo_sum"] - data["spent_txo_sum"])/100_000_000

    else:
        print("address {} not a valid BTC or BTCTEST address".format(address))
        return 0
#Retrueve the full balance of a wallet
def getwalletbalance(wallet: dict):
    #This sum below will be the total balance of the wallet
    sum: float = 0
    #get balances on the parent wallet
    print("Wallet Balances")
    for address in wallet["addresses"].values():
        amount: float = getbalance(address)
        #pending_balance: float() = getpendingbalance(address)
        print(address, amount, wallet["symbol"])
        #add the balance to our total
        sum = amount + sum
    #get balances on the child wallets
    for childwallet in wallet["receiving"]:
        for receiving_address in childwallet["addresses"].values():
            amount: float = getbalance(receiving_address)
            #pending_balance: str = getpendingbalance(receiving_address)
            print(receiving_address, amount, wallet["symbol"])
            #add the balance to our total
            sum = amount + sum
    for childwallet in wallet["change"]:
        for receiving_address in childwallet["addresses"].values():
            amount: float = getbalance(receiving_address)
            #pending_balance: float = getpendingbalance(address)
            print(receiving_address, amount, wallet["symbol"])
            #add the balance to our total
            sum: float = amount + sum
            #Convert the balance to satoshis and truncate anything left over
            #Convert the balance in sats back to a clean btc balance
    sats: int = sum * 100_000_000
    btc: float = sats/100_000_000
    #return the total balance
    return btc

#check if an address is testnet
def is_testnet(address: str):
    if address[0:3] == "tb1" or address[0] == "m" or address[0] == "n" or address[0] == "2":
        return True
#check if an address is mainnet
def is_mainnet(address: str):
    if address[0:3] == "bc1" or address[0] == "1" or address[0] == "3":
        return True
#fetch the UTXOs of an address from the block explorer
def listunspent(address: str):
    if is_testnet(address):
        return bitcoin_testnet_explorer.addr.get_utxo(address).data
    elif is_mainnet(address):
        return bitcoin_explorer.addr.get_utxo(address).data
    else:
        return "Address {} not valid".format(address)

#cerate testnet wallet from seed
def seed_testnet_wallet(seed_phrase: str):
    print("Native Segwit? Y/n")
    #ask which kind of address we're creating
    resp: str = input()
    if resp.lower() == "n":
        print("Please type 'legacy', or 'segwit-p2sh'")
        #user has the option to choose a non segwit address
        resp: str = input()
        if resp.lower() == "legacy":
            derivation = LEGACY
        elif resp.lower() == "segwit-p2sh":
            derivation = SEGWIT_P2SH
        #user input was not understood, default to segwit
        else:
            derivation = SEGWIT_NATIVE
    #default to segwit
    else:
        derivation = SEGWIT_NATIVE
    #create the wallet
    hdwallet: HDWallet = HDWallet(symbol=BTCTEST)
    #build it from our seed phrase
    hdwallet.from_mnemonic(seed_phrase)
    #follow the testnet derivation
    hdwallet.from_index(derivation, hardened=True)
    hdwallet.from_index(1, hardened=True)
    hdwallet.from_index(0, hardened=True)
    #THIS IS A PARENT... CREATE FROM INDEX 0
    hdwallet.from_index(0)
    hdwallet.from_index(0)
    dumps = json.dumps(hdwallet.dumps(), indent=4, ensure_ascii=False)
    loads = json.loads(dumps)
    #remove unnecessary addresses
    clean_addresses(loads)
    #add some space for receiving and change addresses
    loads["receiving"] = []
    loads["change"] = []
    return loads
#Create a testnet wallet from entropy
def create_testnet_wallet():
    STRENGTH: int = 256
    hdwallet: HDWallet = HDWallet(symbol="BTCTEST", use_default_path=False)
    hdwallet.from_entropy(entropy=ENTROPY, language="english", passphrase="")
    LEGACY: int = 44
    SEGWIT_P2SH: int = 49
    SEGWIT_NATIVE: int = 84
    #the first three indexes of derivation are hardened
    #segwit by default
    hdwallet.from_index(SEGWIT_NATIVE, hardened=True)
    hdwallet.from_index(1, hardened=True)
    hdwallet.from_index(0, hardened=True)
    #the last two are not hardened
    hdwallet.from_index(0)
    hdwallet.from_index(0)
    dumps = json.dumps(hdwallet.dumps(), indent=4, ensure_ascii=False)
    loads = json.loads(dumps)
    #remove unnecessary addresses
    clean_addresses(loads)
    #save space for child wallets
    loads["receiving"] = []
    loads["change"] = []
    return loads

def new_wallet(symbol: str, mnemonic: str, derivation: int):
    ENTROPY: str = generate_entropy(strength=STRENGTH)
    hdwallet: HDWallet = HDWallet(symbol=symbol, use_default_path=False)
    if len(mnemonic) > 0:
        hdwallet.from_mnemonic(mnemonic)
    else:
        hdwallet.from_entropy(entropy=ENTROPY, language="english", passphrase="")
    #the first three indexes of derivation are hardened
    #segwit by default
    hdwallet.from_index(derivation, hardened=True)
    if symbol == "BTCTEST":
        hdwallet.from_index(1, hardened=True)
    else:
        hdwallet.from_index(0, hardened=True)
    hdwallet.from_index(0, hardened=True)
    #the last two are not hardened
    hdwallet.from_index(0)
    hdwallet.from_index(0)
    dumps = json.dumps(hdwallet.dumps(), indent=4, ensure_ascii=False)
    loads = json.loads(dumps)
    #remove unnecessary addresses
    clean_addresses(loads)
    #save space for child wallets
    loads["receiving"] = []
    loads["change"] = []
    return loads
