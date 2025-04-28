import asyncio
import logging
import websockets

from ocpp.v201 import call
from ocpp.v201 import ChargePoint as cp
from ocpp.v201.enums import RegistrationStatusEnumType, TriggerReasonEnumType, TransactionEventEnumType

logging.basicConfig(level=logging.INFO)

class ChargePoint(cp):
    async def send_boot_notification(self):
        """ Send BootNotification to the CSMS """
        request = call.BootNotification(
            charging_station={"model": "Server_based_Cp", "vendor_name": "Shrishvesh"},
            reason="PowerUp"
        )

        response = await self.call(request)

        if response.status == RegistrationStatusEnumType.accepted:
            logging.info("Connected to central system.")

    async def start_transaction(self):
        """ Start a transaction and send TransactionEvent to the CSMS """
        request = call.TransactionEvent(
            event_type=TransactionEventEnumType.started,  # Correct enum
            timestamp="2025-03-26T06:44:25.863656+00:00",
            transaction_info={"transaction_id": "1234"},
            trigger_reason=TriggerReasonEnumType.power_up,  # Required field
            seq_no=1  # ✅ Required field
        )
        response = await self.call(request)
        logging.info(f"Transaction started: {response}")

    async def start_operations(self):
        """ Start the boot notification and then handle transactions """
        await self.send_boot_notification()
        await asyncio.sleep(2)  # Ensure CSMS has time to process BootNotification
        await self.start_transaction()

async def main():
    async with websockets.connect(
            'ws://localhost:9000/default',  # Using "/default" as the path
            subprotocols=['ocpp2.0.1']  # Correct subprotocol
    ) as ws:
        cp = ChargePoint('CP_1', ws)
        await cp.start_operations()  # Ensure boot notification & transaction are sent
        await cp.start()  # Keep connection open for further interactions

if __name__ == '__main__':
    asyncio.run(main())
