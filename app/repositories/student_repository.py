from decimal import Decimal
from sqlalchemy import func, case
from app import db
from app.models.student import Student
from app.models.student_ledger import StudentLedger


class StudentRepository:
    """
    Student repository for database operations on the Student model.
    SRP: Single responsibility - only handles Student data access and ledger aggregation.
    """

    @staticmethod
    def get_students_with_balances(search_term=None, only_defaulters=False):
        """Fetches students, their contact info, and their live financial balance from the ledger."""
        try:
            # Subquery to calculate the net balance for every student directly from the ledger
            balance_subq = db.session.query(
                StudentLedger.student_id,
                func.sum(
                    case(
                        (StudentLedger.entry_type == 'DEBIT', StudentLedger.amount),
                        (StudentLedger.entry_type ==
                         'CREDIT', -StudentLedger.amount),
                        else_=0
                    )
                ).label('net_balance')
            ).group_by(StudentLedger.student_id).subquery()

            # Join the core Student profile with the calculated balance
            query = db.session.query(Student, balance_subq.c.net_balance).outerjoin(
                balance_subq, Student.id == balance_subq.c.student_id
            )

            # Apply Omni-Search Filter
            if search_term:
                search = f"%{search_term}%"
                query = query.filter(
                    db.or_(
                        # Search by Student Details
                        Student.first_name.ilike(search),
                        Student.last_name.ilike(search),
                        Student.admission_number.ilike(search),
                        Student.grade_level.ilike(search),

                        # Search by Sponsor/Financial Contact Details
                        Student.sponsor_name.ilike(search),
                        Student.sponsor_phone.ilike(search),
                        Student.sponsor_email.ilike(search)
                    )
                )

            # Order alphabetically by first name
            query = query.order_by(Student.first_name.asc())
            results = query.all()

            output = []

            # Handle boolean or string representations of 'true'
            check_defaulters = str(only_defaulters).lower() == 'true'

            for student, balance in results:
                net_bal = float(balance or 0.0)

                # Filter out cleared students if the Bursar only wants defaulters
                if check_defaulters and net_bal <= 0:
                    continue

                data = student.to_dict()
                data['balance'] = net_bal
                output.append(data)

            return output
        except Exception as e:
            raise e

    @staticmethod
    def get_by_id(student_id):
        """Get a student by their ID."""
        return Student.query.get(student_id)

    @staticmethod
    def get_by_admission_number(admission_number):
        """Get a student by their admission number."""
        return Student.query.filter_by(admission_number=admission_number).first()

    @staticmethod
    def get_by_nemis_upi(nemis_upi):
        """Get a student by their NEMIS UPI."""
        return Student.query.filter_by(nemis_upi=nemis_upi).first()

    @staticmethod
    def get_all():
        """Get all students."""
        return Student.query.all()

    @staticmethod
    def get_with_debt():
        """
        Get all students with outstanding balance (debt).
        Note: This uses the cached current_balance field for speed. 
        For strict audit accuracy, rely on get_students_with_balances.
        """
        return Student.query.filter(Student.current_balance > 0).all()

    @staticmethod
    def create(admission_number, first_name, last_name, parent_phone, nemis_upi=None):
        """Create a new student record."""
        # Check for duplicate admission number
        existing = Student.query.filter_by(
            admission_number=admission_number).first()
        if existing:
            raise ValueError(
                f"Student with admission number {admission_number} already exists")

        student = Student(
            admission_number=admission_number,
            first_name=first_name,
            last_name=last_name,
            parent_phone=parent_phone,
            nemis_upi=nemis_upi,
            current_balance=0.00
        )

        db.session.add(student)
        db.session.flush()  # Get the student.id without committing

        return student

    @staticmethod
    def update_balance(student_id, amount_change):
        """Update student's cached balance (add or subtract amount)."""
        student = Student.query.get(student_id)
        if not student:
            return None

        student.current_balance = (
            student.current_balance or 0) + Decimal(str(amount_change))

        db.session.add(student)
        db.session.flush()

        return student

    @staticmethod
    def set_balance(student_id, new_balance):
        """Set student's cached balance to a specific amount."""
        student = Student.query.get(student_id)
        if not student:
            return None

        student.current_balance = Decimal(str(new_balance))

        db.session.add(student)
        db.session.flush()

        return student

    @staticmethod
    def update(student_id, **kwargs):
        """Update specific student attributes."""
        student = Student.query.get(student_id)
        if not student:
            return None

        # Only allow specific fields to be updated
        allowed_fields = {'first_name', 'last_name',
                          'parent_phone', 'nemis_upi'}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(student, key, value)

        db.session.add(student)
        db.session.flush()

        return student

    @staticmethod
    def delete(student_id):
        """Delete a student record."""
        student = Student.query.get(student_id)
        if not student:
            return False

        db.session.delete(student)
        db.session.flush()

        return True

    @staticmethod
    def count():
        """Count total number of students."""
        return Student.query.count()

    @staticmethod
    def count_with_debt():
        """Count students with outstanding cached balance."""
        return Student.query.filter(Student.current_balance > 0).count()

    @staticmethod
    def create_student(data):
        """Registers a new student into the system."""
        try:
            new_student = Student(
                admission_number=data['admission_number'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                grade_level=data['grade_level'],
                sponsor_name=data['sponsor_name'],
                sponsor_relation=data['sponsor_relation'],
                sponsor_phone=data['sponsor_phone'],
                sponsor_email=data.get('sponsor_email', '')
            )
            db.session.add(new_student)
            db.session.commit()
            return new_student.to_dict()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_student(student_id, data):
        """Updates an existing student's profile or contact details."""
        try:
            student = Student.query.get(student_id)
            if not student:
                raise ValueError("Student not found.")

            # Update allowable fields
            for key in ['first_name', 'last_name', 'grade_level', 'sponsor_name', 'sponsor_relation', 'sponsor_phone', 'sponsor_email']:
                if key in data:
                    setattr(student, key, data[key])

            db.session.commit()
            return student.to_dict()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def deactivate_student(student_id):
        """Soft-deletes a student so they are no longer billed, but preserves financial history."""
        try:
            student = Student.query.get(student_id)
            if not student:
                raise ValueError("Student not found.")

            student.is_active = False
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_ledger_history(student_id):
        """Fetches a student's invoice/payment history ordered newest first."""
        return (
            StudentLedger.query
            .filter_by(student_id=student_id)
            .order_by(StudentLedger.created_at.desc())
            .all()
        )
