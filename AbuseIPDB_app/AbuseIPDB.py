import re
import csv
import json
import os.path
import netaddr
import requests
import ipaddress
import urllib.request as urllib
import urllib.request
from urllib.error import URLError
from Crypto.Random import get_random_bytes
import base64
from io import BytesIO
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP
from dotenv import load_dotenv
import argparse


def is_valid_base64(s):
    # Define a list of valid base64 characters
    valid_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="

    # Check that the string only contains valid characters
    if any(c not in valid_chars for c in s):
        return False

    # Check that the length of the string is a multiple of 4
    if len(s) % 4 != 0:
        return False

    # Check that the string can be decoded without errors
    try:
        # Convert the string to bytes and decode it as base64
        s_bytes = s.encode("utf-8")
        decoded = base64.b64decode(s_bytes)
        # Check that the decoded bytes can be encoded back to the original string
        return base64.b64encode(decoded).decode("utf-8") == s
    except:
        return False


def decrypt_data_b64(b64_string: str, password, key_path):
    file_in = BytesIO(base64.b64decode(b64_string))
    file_in.seek(0)
    try:
        private_key = RSA.import_key(open(key_path).read(), passphrase=password)

        enc_session_key, nonce, tag, ciphertext = \
            [file_in.read(x) for x in (private_key.size_in_bytes(), 16, 16, -1)]
        file_in.close()

        # Decrypt the session key with the private RSA key
        cipher_rsa = PKCS1_OAEP.new(private_key)
        session_key = cipher_rsa.decrypt(enc_session_key)

        # Decrypt the data with the AES session key
        return AES.new(session_key, AES.MODE_EAX, nonce).decrypt_and_verify(ciphertext, tag).decode("utf-8")
    except ValueError:
        print("err: Check Password")
        return False


def encrypt_data_b64(data, key_path):
    if isinstance(data, str):
        data = data.encode("utf-8")
    file_out = BytesIO()
    file_out.seek(0)
    try:
        recipient_key = RSA.import_key(open(key_path).read())
    except ValueError:
        recipient_key = read_rsa_key(key_pass, key_path).public_key().export_key()
        with open(os.path.join(os.path.dirname(key_path), "public_key.bin"), "wb") as pubkey_file_out:
            pubkey_file_out.write(recipient_key)
            pubkey_file_out.close()
        recipient_key = RSA.import_key(read_rsa_key(key_pass, key_path).public_key().export_key())
    session_key = get_random_bytes(16)

    # Encrypt the session key with the public RSA key
    cipher_rsa = PKCS1_OAEP.new(recipient_key)
    enc_session_key = cipher_rsa.encrypt(session_key)

    # Encrypt the data with the AES session key
    cipher_aes = AES.new(session_key, AES.MODE_EAX)
    ciphertext, tag = cipher_aes.encrypt_and_digest(data)
    [file_out.write(x) for x in (enc_session_key, cipher_aes.nonce, tag, ciphertext)]
    bytes_ = file_out.getvalue()
    file_out.close()
    return base64.b64encode(bytes_).decode("utf-8")


def write_rsa_key(password, filepath: str = "key.bin", key_size: int = 4096):
    secret_code = password
    key = RSA.generate(key_size)
    encrypted_key = key.export_key(passphrase=secret_code, pkcs=8,
                                   protection="scryptAndAES128-CBC")
    if not os.path.isdir(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "wb") as file_out:
        file_out.write(encrypted_key)
        file_out.close()

    return key.publickey().export_key()


def read_rsa_key(password, filepath: str = "key.bin"):
    with open(filepath, "rb") as key_file:
        content = key_file.read()
        key_file.close()
        if len(content) > 0:
            return RSA.import_key(content, passphrase=password)

    return False


key_dir = os.path.join(os.getcwd(), "keys")
key_pass = "UnguessablePW1!"
if not os.path.isfile(os.path.join(key_dir, "key.bin")) or len(open(os.path.join(key_dir, "key.bin")).read()) == 0:
    if len(open(os.path.join(key_dir, "key.bin")).read()) == 0:
        os.remove(os.path.join(key_dir, "key.bin"))
    write_rsa_key(
        key_pass,
        filepath=os.path.join(key_dir, "key.bin")
    )

key = read_rsa_key(key_pass, filepath=os.path.join(key_dir, "key.bin"))
print(key)
b64_data = encrypt_data_b64("test", key_path=os.path.join(key_dir, "key.bin"))
print(decrypt_data_b64(b64_data, password="wrong", key_path=os.path.join(key_dir, "key.bin")))
print(decrypt_data_b64(b64_data, password=key_pass, key_path=os.path.join(key_dir, "key.bin")))

# Setup API Key
while os.getenv('API_KEY') is None:
    load_dotenv()
    if os.getenv('API_KEY'):
        if is_valid_base64(os.getenv('API_KEY')):
            api_key = decrypt_data_b64(
                os.getenv('API_KEY'),
                password=key_pass,
                key_path=os.path.join(key_dir, "key.bin")
            )
        else:
            api_key = os.getenv("API_KEY")

    else:
        with open('.env', 'w') as outfile:
            setKey = input(
                'Config File Not Found....\nCreating...\nEnter you API Key for AbuseIPDB: ')
            encrypted_base64 = encrypt_data_b64(setKey, key_path=os.path.join(key_dir, "key.bin"))
            outfile.write(f'API_KEY={encrypted_base64}')
            outfile.close()
            api_key = decrypt_data_b64(
                encrypted_base64,
                password=key_pass,
                key_path=os.path.join(key_dir, "key.bin")
            )


parser = argparse.ArgumentParser(
    description='This program utilizes the Abuse IP Database from: AbuseIPDB.com to perform queries about IP '
                'addresses and returns the output to standard out.'
)

# Inputs
required = parser.add_mutually_exclusive_group()
required.add_argument(
    "-f",
    "--file",
    help="parses IP Addresses from a single given file",
    action="store")
required.add_argument(
    "-i",
    "--ip",
    help="lookup a single IP address",
    action="store")
required.add_argument(
    "-b",
    "--block",
    help="lookup an IP block",
    action="store")
required.add_argument(
    "-cc",
    "--countrycode",
    help="Select a country code to check IP range",
    action="store")

# Outputs
outputs = parser.add_mutually_exclusive_group()
outputs.add_argument(
    "-c", "--csv", help="outputs items in comma seperated values", action="store")
outputs.add_argument(
    "-j", "--json", help="outputs items in json format (reccomended)", action="store")
outputs.add_argument(
    "-l", "--jsonl", help="outputs items in jsonl format (reccomended", action="store")
outputs.add_argument(
    "-t", "--tsv", help="outputs items in tab seperated values (Default)", action="store")

# Additional Options
parser.add_argument(
    "-d", "--days", help="take in the number of days in history to go back for IP reports. Default: 30 Days", type=int)
parser.add_argument("-x", "--translate",
                    help="By default categories are numbers, with this flag it will convert them to text",
                    action="store_true")
parser.add_argument(
    "-v", "--version", help="show program version", action="store_true")

args = parser.parse_args()


def get_cat(x):
    return {
        0: 'BLANK',
        3: 'Fraud_Orders',
        4: 'DDoS_Attack',
        5: 'FTP_Brute-Force',
        6: 'Ping of Death',
        7: 'Phishing',
        8: 'Fraud VoIP',
        9: 'Open_Proxy',
        10: 'Web_Spam',
        11: 'Email_Spam',
        12: 'Blog_Spam',
        13: 'VPN IP',
        14: 'Port_Scan',
        15: 'Hacking',
        16: 'SQL Injection',
        17: 'Spoofing',
        18: 'Brute_Force',
        19: 'Bad_Web_Bot',
        20: 'Exploited_Host',
        21: 'Web_App_Attack',
        22: 'SSH',
        23: 'IoT_Targeted',
    }.get(
        x,
        'UNK CAT, ***REPORT TO MAINTAINER***OPEN AN ISSUE ON GITHUB w/ IP***')


def check_block(ip_block, days):
    if ipaddress.ip_network(ip_block, False).is_private is False:
        headers = {
            'Key': api_key,
            'Accept': 'application/json',
        }

        params = {
            'maxAgeInDays': days,
            'network': f'{ip_block}'
        }

        while True:
            r = requests.get(
                'https://api.abuseipdb.com/api/v2/check-block', headers=headers, params=params)
            if r.status_code == 503:
                print(
                    f"Error: abuseIPDB returned a 503 for {ip_block}")
            else:
                break

        response = r.json()
        if 'errors' in response:
            print(f"Error: {response['errors'][0]['detail']}")
            exit(1)
        else:
            logs = []
            logs.append(response['data'])
            return logs

    else:
        return (f"{ip_block} is a private block")


def check_ip(IP, days):
    if ipaddress.ip_address(IP).is_private is False:
        headers = {
            'Key': api_key,
            'Accept': 'application/json',
        }

        params = {
            'maxAgeInDays': days,
            'ipAddress': IP,
            'verbose': ''
        }

        r = requests.get('https://api.abuseipdb.com/api/v2/check',
                         headers=headers, params=params)
        response = r.json()
        if 'errors' in response:
            print(f"Error: {response['errors'][0]['detail']}")
            exit(1)
        else:
            if args.translate:
                if response['data']['totalReports'] > 0:
                    for report in response['data']['reports']:
                        tmp_catergory = []
                        category = report['categories']
                        for cat in category:
                            tmp_catergory.append(get_cat(cat))
                        report['categories'] = tmp_catergory
            return response['data']
    else:
        return (f"{IP} is private. No Resuls")


def check_file(file, days):
    logs = []
    found = []
    with open(file) as f:
        file_item = f.read()
        regex = r'(?:(?:2(?:[0-4][0-9]|5[0-5])|[0-1]?[0-9]?[0-9])\.){3}(?:(?:2([0-4][0-9]|5[0-5])|[0-1]?[0-9]?[0-9]))'

        matches = re.finditer(regex, file_item, re.MULTILINE)

        [found.append(match.group())
         for matchNum, match in enumerate(matches, start=1)]
        found = set(found)
        for match in found:
            logs.append(check_ip(match, days))
    return logs


def make_subnet(block):
    # Setting to /24 as AbuseIPDB doesn't support anything larger
    ip = netaddr.IPNetwork(block)
    return list(ip.subnet(24))


def search_cc(days):
    logs = []
    url = f"https://www.nirsoft.net/countryip/{args.countrycode}.csv"
    try:
        with urllib.request.urlopen(url) as x:
            ip_blocks = x.read().decode('utf-8')
            cr = csv.reader(ip_blocks.splitlines())
            for row in cr:
                if row:
                    startip = row[0]
                    endip = row[1]
                    block = netaddr.iprange_to_cidrs(startip, endip)[0]
                    subnets = make_subnet(block)
                    for ip_range_24 in subnets:
                        logs.append(check_block(ip_range_24, days))
                return logs

    except URLError as e:
        if '404' in str(e):
            print(f"{url} not a valid url")
            print(
                "List of countries codes can be found at https://www.nirsoft.net/countryip/")
        else:
            print(f"Error: {e.reason}")

        exit()


def get_report(logs):
    if logs:
        # Output options
        if args.csv:
            try:
                keys = logs[0].keys()
            except KeyError:
                keys = logs.keys()

            with open(args.csv, 'w') as outfile:
                dict_writer = csv.DictWriter(
                    outfile, keys, quoting=csv.QUOTE_ALL)
                dict_writer.writeheader()
                dict_writer.writerows(logs)
            pass
        elif args.tsv:
            keys = logs[0].keys()
            with open(args.tsv, 'w') as outfile:
                dict_writer = csv.DictWriter(outfile, keys, delimiter='\t')
                dict_writer.writeheader()
                dict_writer.writerows(logs)
            pass
        elif args.jsonl:
            json_logs = json.dumps(logs)
            with open(args.jsonl, 'w') as outfile:
                for log in logs:
                    json.dump(log, outfile)
                    outfile.write('\n')
            pass
        elif args.json:
            with open(args.json, 'w') as outfile:
                json.dump(logs, outfile, indent=4, sort_keys=True)
            pass
        else:
            print(logs)
            pass
    else:
        pass


def main():
    if args.days:
        days = args.days
    else:
        days = 30

    if args.file:
        get_report(check_file(args.file, days))
    elif args.ip:
        get_report(check_ip(args.ip, days))
    elif args.block:
        regex = r'^([0-9]{1,3}\.){3}[0-9]{1,3}(\/([2][4-9]|3[0-2]))?$'
        valid_block = re.findall(regex, args.block)
        if valid_block:
            get_report(check_block(args.block, days))
        else:
            exit(
                "Not valid CIDR or Not within the accepted Block. Note: AbuseIPDB only accepts /24+")
    elif args.countrycode:
        get_report(search_cc(days))
    elif args.version:
        print(f"{parser.prog} Version: 2.1")
    else:
        exit(
            "Error: one of the following arguments are required: -f/--file, -i/--ip, -b/--block or -cc/--countrycode")


if __name__ == '__main__':
    main()
