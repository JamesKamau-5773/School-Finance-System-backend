from .auth import Role, User
from .finance import VoteHead, Supplier, Transaction, LedgerEntry
from .inventory import InventoryItem, StockTransaction, StoreTransaction
from .fee_structure import FeeStructure
from .student_ledger import StudentLedger
from .student import Student

# Backward-compatible aliases for older test modules.
Inventory = InventoryItem
InventoryLog = StockTransaction
