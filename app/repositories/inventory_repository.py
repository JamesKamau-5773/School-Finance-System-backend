from app.models.inventory import Inventory, InventoryLog
from app import db


class InventoryRepository:
    @staticmethod
    def get_all_items():
        return Inventory.query.all()

    @staticmethod
    def get_item_by_id(item_id):
        return Inventory.query.get(item_id)

    @staticmethod
    def update_stock_level(item_id, quantity_change):
        item = Inventory.query.get(item_id)
        if item:
            item.current_quantity += quantity_change
            db.session.add(item)
            return item
        return None

    @staticmethod
    def add_log(log_data):
        new_log = InventoryLog(**log_data)
        db.session.add(new_log)
        return new_log
