import asyncio
import logging
from datetime import datetime,timezone
try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)


from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call
from ocpp.v201 import call_result

logging.basicConfig(level=logging.INFO)


class ChargePoint(cp):
    async def send_heartbeat(self, interval):
        request = call.Heartbeat()
        while True:
            await self.call(request)
            await asyncio.sleep(interval)

    async def send_boot_notification(self):
        request = call.BootNotification(
            charging_station={"model": "scorpio26", "vendor_name": "shrishvesh"},
            reason="PowerUp",
        )
        response = await self.call(request)

        if response.status == "Accepted":
            print("Connected to central system.")
            await self.send_heartbeat(response.interval)
            
            
    async def send_start_transaction(self):
        current_time = datetime.now(timezone.utc).isoformat()
        request = call.TransactionEvent(
            event_type="Started",
            timestamp=current_time,  # current UTC time
            trigger_reason="Authorized",
            seq_no=1,
            evse={"id": 1, "connector_id": 1},
            id_token={"id_token": "abc123", "type": "Central"},
            meter_value=[{
                "timestamp": current_time,
                "sampled_value": [{"value": 0, "measurand": "Energy.Active.Import.Register"}]
            }],
            transaction_info={
                "transaction_id": "tx12345",
                "charging_state": "Charging",   # assuming ChargingStateEnumType.Charging
                "time_spent_charging": 0,
                "stopped_reason": None,
                "remote_start_id": None
            },
            custom_data={
            "vendorId": "shrishvesh_vendor",  # Add the required vendorId here
            "current_charging": 0,
            "final_charging": 0
            }
            
        )
        response = await self.call(request)
        logging.info(f"TransactionEvent response received: {response}")

async def main():
    async with websockets.connect(
        "ws://localhost:9000/CP_1", subprotocols=["ocpp2.0.1"]
    ) as ws:

        charge_point = ChargePoint("CP_1", ws)
        await asyncio.gather(
            charge_point.start(), charge_point.send_boot_notification()
        )


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())