import datetime
import json
import http.client
import threading
from phBot import *

pName = "SilkroadMarketOnline"
pVersion = "1.0.1"

# Globals
lock = threading.Lock()
previous_packet = None
currentIndex = 0
last_stall_reset_time = None  # Timestamp for debounce


# Character and Inventory Data
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


# Safe Update for Previous Packet
def safe_update_previous_packet(packet):
    """Thread-safe update for the previous_packet variable."""
    global previous_packet
    try:
        if lock.acquire(timeout=1):  # Wait up to 1 second for the lock
            log("Lock acquired. Updating previous_packet.")
            previous_packet = packet
        else:
            log(
                "Failed to acquire lock for updating previous_packet. Possible contention."
            )
    finally:
        if lock.locked():
            lock.release()
            log("Lock released after updating previous_packet.")


# API Call to Post Stall Data
def postStallData(packetData, isFirstItem):
    """
    Sends the raw packet bytes to the API along with metadata.
    """
    # Prepare payload
    payload = json.dumps(
        {
            "bytes": packetData.hex(),  # Use the raw packet data, converted to hex
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

    # Send the payload to the API
    try:
        conn = http.client.HTTPSConnection("silkroadmarket.online")
        conn.request("POST", "/api/v1/stall", payload, headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()

        if response.status in (200, 201):
            log(f"API Success: {response.status}")
        else:
            log(f"API Error: {response.status} - {data.decode('utf-8')}")
    except Exception as e:
        log(f"API Exception: {e}")


# Handle Joymax Packets
def handle_joymax(opcode, data):
    global currentIndex, previous_packet
    if data is None:
        return True

    if opcode != 0xB0BA:
        return True

    # Convert data to hex string for logging
    packetBytes = " ".join(f"{x:02X}" for x in data)

    log(f"Packet Received (Opcode {opcode:04X}): {packetBytes}")

    # Ensure we're not processing irrelevant packets
    if tuple(data) not in [(0x01, 0x05, 0x01), (0x02, 0x13, 0x3C)]:
        try:
            # Safely update the previous packet
            safe_update_previous_packet(packetBytes)

            # If no previous packet exists, treat the current one as is
            if previous_packet is None:
                log("Uploading first item.")
                postStallData(data, isFirstItem=True)
            else:
                # Use the entire packet if no meaningful previous packet exists
                log("Uploading non-first item.")
                postStallData(data, isFirstItem=False)

            currentIndex += 1
        except Exception as e:
            log(f"Error in handle_joymax: {e}")

    return True


# Reset Index on Stall Open (Debounced)
def reset_current_index():
    global currentIndex, last_stall_reset_time
    now = datetime.datetime.now()

    # Debounce logic: only reset if at least 1 second has passed since the last reset
    if (
        last_stall_reset_time is None
        or (now - last_stall_reset_time).total_seconds() > 1
    ):
        log("Stall has been opened. Resetting current index.")
        currentIndex = 0
        last_stall_reset_time = now


# # Main Entry Point
# def event_loop():
#     """Event loop to handle Joymax packets."""
#     global currentIndex

#     # Simulate resetting index when a stall is opened
#     reset_current_index()

log("Plugin: " + pName + " v" + pVersion + " successfully loaded")
