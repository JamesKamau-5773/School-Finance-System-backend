from app import db
from datetime import datetime

class FeeStructure(db.Model):
    __tablename__ = 'fee_structures'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)          # e.g., "Term 1 Lunch Program"
    amount = db.Column(db.Numeric(10, 2), nullable=False)     # e.g., 4000.00
    academic_year = db.Column(db.String(9), nullable=False)   # e.g., "2026"
    term = db.Column(db.String(20), nullable=False)           # e.g., "Term 1"
    target_cohort = db.Column(db.String(50), nullable=False)  # e.g., "Form 1", "All Students"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50), nullable=False)     # Admin/Principal ID who authorized it

    # Relationship to the invoices generated from this structure
    student_entries = db.relationship('StudentLedger', backref='fee_source', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "amount": float(self.amount),
            "academic_year": self.academic_year,
            "term": self.term,
            "target_cohort": self.target_cohort,
            "is_active": self.is_active
        }