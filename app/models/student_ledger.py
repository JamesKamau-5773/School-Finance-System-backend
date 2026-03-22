from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID


class StudentLedger(db.Model):
    __tablename__ = 'student_ledgers'

    id = db.Column(db.Integer, primary_key=True)
    # Creates a strict relational link to the actual student record
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id'), nullable=False)

    # If this is an invoice, it links back to the FeeStructure rule
    fee_structure_id = db.Column(db.Integer, db.ForeignKey(
        'fee_structures.id'), nullable=True)

    # 'INVOICE' (increases student debt) or 'PAYMENT' (decreases student debt)
    entry_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)

    description = db.Column(db.String(255), nullable=False)
    reference_no = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "entry_type": self.entry_type,
            "amount": float(self.amount),
            "description": self.description,
            "reference_no": self.reference_no,
            "date": self.created_at.strftime("%Y-%m-%d %H:%M")
        }
