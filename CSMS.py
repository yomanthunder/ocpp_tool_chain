import asyncio
import logging
import websockets
from datetime import datetime, timezone

from ocpp.routing import on
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call, call_result
from ocpp.v201.enums import (
    RegistrationStatusEnumType, MessageTriggerEnumType, ReasonEnumType, 
    TransactionEventEnumType, TriggerReasonEnumType
)

logging.basicConfig(level=logging.INFO)

class ChargePoint(cp):
    @on('BootNotification')
    async def on_boot_notification(self, charging_station, reason, **kwargs):
        logging.info(f"BootNotification received: {charging_station}, Reason: {reason}")
        return call_result.BootNotification(
            current_time=datetime.now(timezone.utc).isoformat(),
            interval=10,
            status=RegistrationStatusEnumType.accepted
        )
    
    async def send_heartbeat(self):
        """Send a periodic heartbeat."""
        while True:
            await asyncio.sleep(5)  # Send heartbeat every 5s
            request = call.Heartbeat()
            response = await self.call(request)
            logging.info(f"Heartbeat Response: {response.current_time}")

    async def start_transaction(self):
        """Start a simulated charging transaction."""
        logging.info("Starting Charging Transaction...")

        transaction_id = "TX123456"  # Fake Transaction ID
        request = call.TransactionEvent(
            event_type=TransactionEventEnumType.started,
            timestamp=datetime.now(timezone.utc).isoformat(),
            transaction_info={"transaction_id": transaction_id},
            trigger_reason=TriggerReasonEnumType.power_up,  #  Required field
            seq_no=1  # Required field
        )
        response = await self.call(request)
        logging.info(f"Transaction Started: {response}")

        # Send periodic meter values
        await self.send_meter_values(transaction_id)

        # Stop transaction after 10 seconds
        await asyncio.sleep(10)
        await self.stop_transaction(transaction_id)

    async def send_meter_values(self, transaction_id):
        """Send fake meter readings."""
        meter_value = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sampled_value": [{"value": "15.3", "unit": "kWh"}]  # Fake energy reading
        }

        request = call.MeterValuesRequest(
            transaction_id=transaction_id,
            meter_value=[meter_value]
        )
        response = await self.call(request)
        logging.info(f"Meter Values Sent: {response}")

    async def stop_transaction(self, transaction_id):
        """Stop a charging transaction."""
        logging.info("Stopping Charging Transaction...")

        request = call.TransactionEvent(
            event_type=TransactionEventEnumType.ended,
            timestamp=datetime.now(timezone.utc).isoformat(),
            transaction_info={"transaction_id": transaction_id},
            trigger_reason=TriggerReasonEnumType.ev_stop,  #  Required field
            reason=ReasonEnumType.ev_disconnected,
            seq_no=2  # Required field
        )
        response = await self.call(request)
        logging.info(f"Transaction Stopped: {response}")


async def on_connect(websocket, path="/default"):
    logging.info(f"New connection attempt on path: {path}")

    if websocket.subprotocol != "ocpp2.0.1":
        logging.warning(f"Protocol mismatch. Expected: 'ocpp2.0.1', but got: '{websocket.subprotocol}'. Closing connection.")
        return await websocket.close()

    charge_point_id = path.strip('/') if path else "default"
    logging.info(f"Charge Point ID: {charge_point_id}")

    cp = ChargePoint(charge_point_id, websocket)

    try:
        await cp.start()  # This listens for messages until the connection is closed
    except websockets.exceptions.ConnectionClosed:
        logging.info(f"Connection closed for Charge Point: {charge_point_id}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")


    # # Start background tasks
    # asyncio.create_task(cp.send_heartbeat())
    # asyncio.create_task(cp.start_transaction())

async def main():
    server = await websockets.serve(
        on_connect,
        "0.0.0.0",
        9000,
        subprotocols=["ocpp2.0.1"]
    )
    logging.info("WebSocket Server Started on ws://0.0.0.0:9000")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
