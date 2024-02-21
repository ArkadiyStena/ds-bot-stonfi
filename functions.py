import logging
from datetime import datetime, timedelta

import requests
from pytonconnect import TonConnect
from pytonconnect.storage import FileStorage
from config import *
from tc_storage import SimpleStorage


# def get_wallets_dict() -> dict[str, str]:
#     with open("wallets.csv") as f:
#         all_wallets = {}
#         for elem in f.read().split('\n')[1:]:
#             elem = elem.split(';')
#             all_wallets[int(elem[0])] = elem[2]
#         return all_wallets


def add_wallet(user_id: int, username: str, wallet_address: str) -> None:
    """adds new wallet to the storage"""
    with open("wallets.csv", 'a') as f:
        f.write(f"\n{user_id};{username};{wallet_address}")


def remove_wallet(user_id: int) -> bool:
    """removes data about user with the given user_id"""
    with open("wallets.csv") as f:
        wallets = f.read()
        line_start_index = wallets.find(str(user_id) + ';')
    if line_start_index != -1:
        line_end_index = wallets.find('\n', line_start_index)
        with open("wallets.csv", 'w') as f:
            if line_end_index != -1:
                f.write(wallets[:line_start_index] + wallets[line_end_index + 1:])
            else:
                f.write(wallets[:line_start_index - 1])
        return True
    return False
    

def get_wallet(user_id: int) -> str | None:  
    """returns user's wallet address by the given user_id"""
    with open("wallets.csv") as f:
        wallets = f.read()
        line_start_index = wallets.find(str(user_id) + ';')
    if line_start_index != -1:
        line_end_index = wallets.find('\n', line_start_index)
        if line_end_index != -1:
            return wallets[line_start_index:line_end_index].split(';')[2]
        else:
            return wallets[line_start_index:].split(';')[2]
    return None


def check_wallet(wallet_address) -> bool:
    """checks weather the wallet with the given address is already connected"""
    with open("wallets.csv") as f:
        return wallet_address in f.read()
    

async def get_connector(user_id: str, wallet_name: str = 'Tonkeeper') -> tuple[str, TonConnect]:
    """starts wallet connect proccess and returns tuple(connection_link, connector)"""
    storage = SimpleStorage(user_id)
    connector = TonConnect(manifest_url=TONCONNECT_MANIFEST_URL, storage=storage)

    await connector.restore_connection()
    if connector.connected:
        await connector.disconnect()

    def status_changed(wallet_info):
        unsubscribe()

    def status_error(e):
        pass

    unsubscribe = connector.on_status_change(status_changed, status_error)
    wallets_list = connector.get_wallets()
    for wallet in wallets_list:
        if wallet["name"] == wallet_name:
            return ((await connector.connect(wallet)) + "&ret=back", connector) 
        

async def disconnect_wallet(user_id: str) -> None:
    storage = SimpleStorage(user_id)
    connector = TonConnect(manifest_url=TONCONNECT_MANIFEST_URL, storage=storage)
    await connector.restore_connection()
    if connector.connected:
        await connector.disconnect()


def get_traded_volume(wallet_address: str, start_date: datetime = None, end_date: datetime = None) -> float:
    """returns total traded volume in TON pools"""
    url = f"https://api.ston.fi/v1/wallets/{wallet_address}/operations"

    if start_date is None and end_date is None:
        end_date = datetime.now()
    elif end_date is None:
        end_date = start_date + timedelta(days=30)
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    params = {
        "since": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "until": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "op_type": "Swap",
    }
    try:
        operations = requests.get(url, params).json()["operations"]
    except Exception:
        return 0

    total_volume = 0
    for operation in operations:
        operation = operation["operation"]
        if operation["asset0_address"] == PTON_ADDRESS:
            pton_index = 0
        elif operation["asset1_address"] == PTON_ADDRESS:
            pton_index = 1
        else:
            continue
        operation_volume = abs(int(operation[f"asset{pton_index}_amount"]))
        total_volume += operation_volume

    return round(total_volume / 1e9, 2)
