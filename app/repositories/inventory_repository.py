import uuid
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from app import db
from app.models.inventory import InventoryItem, StockTransaction, StoreTransaction


class InventoryRepository:

    ACTION_MAP = {
        'in': 'received',
        'received': 'received',
        'stock_in': 'received',
        'out': 'issued',
        'issued': 'issued',
        'consumption': 'issued'
    }

    @staticmethod
    def _to_decimal(value, field_name='value'):
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(f"Invalid {field_name}: {value}")

    @staticmethod
    def _to_uuid(value, field_name='id'):
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            raise ValueError(f"Invalid {field_name}: {value}")

    @staticmethod
    def _to_integer_decimal(value, field_name='value', min_value=0):
        decimal_value = InventoryRepository._to_decimal(value, field_name)

        if decimal_value != decimal_value.to_integral_value():
            raise ValueError(f"{field_name} must be a whole number")

        min_decimal = Decimal(str(min_value))
        if decimal_value < min_decimal:
            raise ValueError(f"{field_name} must be at least {min_value}")

        return decimal_value

    @staticmethod
    def get_all_items():
        """Fetches the current real-time stock balances for the dashboard."""
        items = InventoryItem.query.filter_by(
            is_active=True).order_by(InventoryItem.name).all()
        return [item.to_dict() for item in items]

    @staticmethod
    def get_item_by_id(item_id):
        """Fetches a single inventory item profile by its ID."""
        item = InventoryItem.query.get(item_id)
        return item.to_dict() if item else None

    @staticmethod
    def create_item(data):
        """Registers a new physical asset or consumable into the Store catalog."""
        try:
            new_item = InventoryItem(
                item_code=data['item_code'].upper(),
                name=data['name'],
                category=data['category'],
                unit_of_measure=data['unit_of_measure'],
                reorder_level=InventoryRepository._to_integer_decimal(data.get('reorder_level', 0), 'reorder_level', min_value=0)
            )
            db.session.add(new_item)
            db.session.commit()
            return new_item.to_dict()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def record_transaction(item_id, data, user_id=None):
        """
        The core inventory engine. Handles IN/OUT movements with strict row-locking 
        to prevent negative stock balances and race conditions.
        """
        try:
            # 1. Fetch the item and strictly LOCK the row until this transaction finishes
            item_uuid = InventoryRepository._to_uuid(item_id, 'item_id')
            user_uuid = InventoryRepository._to_uuid(user_id, 'recorded_by') if user_id else None
            item = db.session.query(InventoryItem).filter_by(
                id=item_uuid).with_for_update().first()

            if not item:
                raise ValueError("Inventory item not found.")

            transaction_type = data['transaction_type'].upper()
            qty = InventoryRepository._to_integer_decimal(data['quantity'], 'quantity', min_value=1)

            # 2. Enforce Stock Physics
            if transaction_type == 'IN':
                item.current_stock += qty
            elif transaction_type == 'OUT':
                if item.current_stock < qty:
                    raise ValueError(
                        f"Insufficient stock. Cannot issue {qty} {item.unit_of_measure}. Only {item.current_stock} available.")
                item.current_stock -= qty
            else:
                raise ValueError(
                    "Invalid transaction type. Must be 'IN' or 'OUT'.")

            # 3. Create the Immutable Audit Record
            new_transaction = StockTransaction(
                item_id=item.id,
                transaction_type=transaction_type,
                quantity=qty,
                party_name=data['party_name'],
                reference_no=data.get('reference_no'),
                remarks=data.get('remarks'),
                recorded_by=user_uuid  # The UUID of the logged-in Storekeeper
            )

            action = InventoryRepository.ACTION_MAP.get(
                transaction_type.lower(), transaction_type.lower())
            ledger_entry = StoreTransaction(
                item_id=item.id,
                recorded_by=user_uuid,
                action=action,
                quantity=int(qty)
            )

            db.session.add(new_transaction)
            db.session.add(ledger_entry)

            # 4. Commit both the item update and the transaction log simultaneously
            db.session.commit()
            return new_transaction.to_dict()

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_item_ledger(item_id):
        """Fetches the chronological movement history for a specific item."""
        transactions = StockTransaction.query.filter_by(
            item_id=item_id).order_by(StockTransaction.created_at.desc()).all()
        return [tx.to_dict() for tx in transactions]

    @staticmethod
    def get_filtered_transactions(filters):
        query = db.session.query(StoreTransaction).join(
            InventoryItem, StoreTransaction.item_id == InventoryItem.id)

        category = (filters.get('category') or '').strip()
        if category:
            query = query.filter(InventoryItem.category.ilike(category))

        action = (filters.get('action') or '').strip().lower()
        if action:
            mapped_action = InventoryRepository.ACTION_MAP.get(action, action)
            query = query.filter(StoreTransaction.action == mapped_action)

        item_id = (filters.get('item_id') or '').strip()
        if item_id:
            query = query.filter(StoreTransaction.item_id == InventoryRepository._to_uuid(item_id, 'item_id'))

        recorded_by = (filters.get('recorded_by') or '').strip()
        if recorded_by:
            query = query.filter(StoreTransaction.recorded_by == InventoryRepository._to_uuid(recorded_by, 'recorded_by'))

        start_date = (filters.get('start_date') or '').strip()
        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(StoreTransaction.created_at >= start_dt)

        end_date = (filters.get('end_date') or '').strip()
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(StoreTransaction.created_at < end_dt)

        limit = min(int(filters.get('limit', 200)), 1000)
        offset = max(int(filters.get('offset', 0)), 0)

        transactions = query.order_by(
            StoreTransaction.created_at.desc()).offset(offset).limit(limit).all()
        return [tx.to_dict() for tx in transactions]

    @staticmethod
    def update_item(item_id, data):
        """Updates an existing inventory catalog item."""
        try:
            item = InventoryItem.query.get(item_id)
            if not item:
                raise ValueError("Inventory item not found.")
            
            # Update allowable fields
            if 'name' in data: item.name = data['name']
            if 'category' in data: item.category = data['category']
            if 'unit_of_measure' in data: item.unit_of_measure = data['unit_of_measure']
            if 'reorder_level' in data:
                item.reorder_level = InventoryRepository._to_integer_decimal(data['reorder_level'], 'reorder_level', min_value=0)
            
            # Note: We do NOT allow updating current_stock here. That must be done via transactions.
            
            db.session.commit()
            return item.to_dict()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def deactivate_item(item_id):
        """Soft-deletes an item so it stops showing up in the active dashboard."""
        try:
            item = InventoryItem.query.get(item_id)
            if not item:
                raise ValueError("Inventory item not found.")
            
            item.is_active = False
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e