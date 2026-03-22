from app import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admission_number = db.Column(
        db.String(50), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)

    # Classification (e.g., "Grade 10", "Form 3")
    grade_level = db.Column(db.String(50), nullable=False, index=True)

    # --- Communication & Billing Contacts ---
    sponsor_name = db.Column(db.String(100), nullable=False)
    
    sponsor_relation = db.Column(db.String(50), nullable=False)
    
    sponsor_phone = db.Column(db.String(20), nullable=False)
    
    sponsor_email = db.Column(db.String(120), nullable=True)

    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

   
    ledger_entries = db.relationship(
        'StudentLedger', backref='student_profile', lazy=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "admission_number": self.admission_number,
            "full_name": f"{self.first_name} {self.last_name}",
            "grade_level": self.grade_level,
            "sponsor": {
                "name": self.sponsor_name,
                "relation": self.sponsor_relation,
                "phone": self.sponsor_phone,
                "email": self.sponsor_email
            },
            "is_active": self.is_active
        }
