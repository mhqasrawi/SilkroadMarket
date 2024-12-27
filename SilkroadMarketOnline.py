import datetime
import json
import http.client
import struct
import time
from phBot import *
import threading

pName = "SilkroadMarketOnline"
pVersion = "1.0.0"


def getInventory():
    items = get_inventory()["items"]
    filtered_items = [item for item in items if item is not None]
    return filtered_items


charData = get_character_data()
invItems = getInventory()
charName = charData["name"]
xAxis = int(charData["x"])
yAxis = int(charData["y"])
serverName = charData["server"]
region = int(charData["region"])

API_KEY = "PLACE YOUR API KEY HERE"

previous_packet = ""
currentIndex = 0


def postStallData(packetBytes, isFirstItem):
    conn = http.client.HTTPSConnection("silkroadmarket.online")
    payload = json.dumps(
        {
            "bytes": packetBytes.hex(),
            "charName": charName,
            "isFirstItem": isFirstItem,
            "items": invItems,
            "xAxis": xAxis,
            "yAxis": yAxis,
            "serverName": serverName,
            "region": region,
        }
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY,
    }
    try:
        conn.request("POST", "/api/v1/stall", payload, headers)
        response = conn.getresponse()
        data = response.read()
        if response.status == 200 or response.status == 201:
            log("Item added successfully")
        else:
            log(
                f"API Response: {data.decode('utf-8')} for Packet {packetBytes.hex()} and invItems: {invItems}"
            )
    except Exception as e:
        log(f"API Error: {e}")
    finally:
        conn.close()
        return True


def handle_joymax(opcode, data):
    global previous_packet, currentIndex
    current_time = datetime.datetime.now().strftime("%H:%M:%S")

    if opcode == 0xB0BA and data != None and tuple(data) == (0x01, 0x05, 0x01):
        currentIndex = 0
        log("Stall Has Been Opened Resetting Current Index")

    if data is None:
        return True

    if opcode != 0xB0BA:
        return True

    packetBytes = "None" if not data else " ".join("{:02X}".format(x) for x in data)
    packet_tuple = tuple(data)

    if (
        opcode == 0xB0BA
        and packet_tuple != (0x01, 0x05, 0x01)
        and packet_tuple != (0x02, 0x13, 0x3C)
    ):
        current_packet = packetBytes.rstrip(" FF")

        if previous_packet:
            new_packet = current_packet.replace(previous_packet, "").strip()
        else:
            new_packet = current_packet

        previous_packet = current_packet

        if currentIndex == 0:
            log("Uploading First Item")
            firstItemPacket = bytes.fromhex(new_packet + " FF")

            postStallData(firstItemPacket, True)

        else:
            log("Uploading Non First Item")
            nonFirstItemPacket = bytes.fromhex(new_packet + " FF")

            return postStallData(nonFirstItemPacket, False)

        currentIndex += 1

    return True


log("Plugin: " + pName + " v" + pVersion + " successfully loaded")
