import asyncio
import logging
from datetime import datetime, timezone
from ocpp.routing import on
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call_result
from ocpp.v201.enums import Action
import serial
import json

 
logging.basicConfig(level=logging.INFO)

SERIAL_PORT = '/dev/ttyAMA)'  # Adjust based on your setup
BAUD_RATE = 115200            # Or whatever you're using
COST_PER_KWH = 5              # ₹ per kWh or adjust unit

def get_energy_cost_from_tms(current, final):
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            payload = {
                "current_charge": current,
                "final_charge": final
            }
            ser.write((json.dumps(payload) + '\n').encode())

            # Wait for response from TMS
            line = ser.readline().decode().strip()
            if not line:
                raise Exception("No response from TMS320")
            
            response = json.loads(line)
            # Example response: { "energy_used": 1.2 }
            energy_used = response.get("energy_used", 0)
            total_cost = energy_used * COST_PER_KWH
            time_op = 0 #subtyract time before and after execution 
            return total_cost, energy_used,time_op

    except Exception as e:
        print(f"Serial communication error: {e}")
        return 0, 0 

class ChargePoint(cp):
    @on(Action.boot_notification)
    def on_boot_notification(self, charging_station, reason, **kwargs):
        return call_result.BootNotification(
            current_time=datetime.now(timezone.utc).isoformat(), interval=10, status="Accepted"
        )

    @on(Action.heartbeat)
    def on_heartbeat(self):
        print("Got a Heartbeat!")
        return call_result.Heartbeat(
            current_time=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        )
    @on(Action.transaction_event)
    async def on_start_transaction(self, **kwargs):
        print("Received TransactionEvent from charge point!")

        # Log important details
        print(f"TransactionEvent type: {kwargs}")
        # print(f"EVSE ID: {event.evse['id']}")
        # print(f"Connector ID: {event.evse['connector_id']}")
        # print(f"ID Token: {event.id_token['id_token']}")

        # You can store this information in a database if you want.

        # Now respond back to the charge point
        response = call_result.TransactionEvent(
            total_cost=0,
            charging_priority=0,
            id_token_info={"status": "Accepted"},
            updated_personal_message=None
        )
        return response
    
    
async def on_connect(websocket):
    """For every new charge point that connects, create a ChargePoint
    instance and start listening for messages.
    """
    try:
        requested_protocols = websocket.request.headers["Sec-WebSocket-Protocol"]
    except KeyError:
        logging.error("Client hasn't requested any Subprotocol. Closing Connection")
        return await websocket.close()
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        # In the websockets lib if no subprotocols are supported by the
        # client and the server, it proceeds without a subprotocol,
        # so we have to manually close the connection.
        logging.warning(
            "Protocols Mismatched | Expected Subprotocols: %s,"
            " but client supports %s | Closing connection",
            websocket.available_subprotocols,
            requested_protocols,
        )
        return await websocket.close()

    charge_point_id = websocket.request.path.strip("/")
    charge_point = ChargePoint(charge_point_id, websocket)

    # loss of websocket connection handled gracefully 
    try:
        logging.info(f"Charge point '{charge_point_id}' connected.")
        await charge_point.start()
    except websockets.exceptions.ConnectionClosed as e:
        logging.warning(f"Connection to charge point '{charge_point_id}' closed: {e.code} - {e.reason}")
    except Exception as e:
        logging.exception(f"Unexpected error with charge point '{charge_point_id}': {e}")
    finally:
        # Perform any cleanup here
        logging.info(f"Charge point '{charge_point_id}' disconnected.")


async def main():
    #  deepcode ignore BindToAllNetworkInterfaces: <Example Purposes>
    server = await websockets.serve(
        on_connect, "0.0.0.0", 9000, subprotocols=["ocpp2.0.1"]
    )

    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())