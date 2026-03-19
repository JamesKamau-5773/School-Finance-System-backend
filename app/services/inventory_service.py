from app.repositories.inventory_repository import InventoryRepository
from app import db


class InventoryService:
    @staticmethod
    def record_usage(item_id, quantity_used, user_id, remarks):
        item = InventoryRepository.get_item_by_id(item_id)
        if not item or item.current_quantity < quantity_used:
            return {"error": "Insufficient stock in store"}, 400

        try:
            # 1. Update the physical balance
            InventoryRepository.update_stock_level(item_id, -quantity_used)

            # 2. Log the transaction for audit purposes
            InventoryRepository.add_log({
                'inventory_id': item_id,
                'quantity': -quantity_used,
                'transaction_type': 'CONSUMPTION',
                'recorded_by': user_id,
                'remarks': remarks
            })

            db.session.commit()

            # 3. Trigger Early Warning if below threshold
            warning = None
            if item.current_quantity <= item.reorder_level:
                warning = f"Low stock alert: Only {item.current_quantity} {item.unit_of_measure} remaining."

            return {
                "message": "Consumption recorded",
                "remaining_stock": float(item.current_quantity),
                "alert": warning
            }, 201
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @staticmethod
    def get_stock_predictions():
        """
        Predicts how many days of stock remain.
        Logic: $Days = \frac{Current Quantity}{Average Daily Consumption}$
        """
        items = InventoryRepository.get_all_items()
        predictions = []

        for item in items:
            days_left = float('inf')
            if item.average_daily_consumption > 0:
                days_left = float(item.current_quantity /
                                  item.average_daily_consumption)

            predictions.append({
                "item": item.item_name,
                "current_quantity": float(item.current_quantity),
                "unit": item.unit_of_measure,
                "days_remaining": round(days_left, 1)
            })

        return predictions, 200
