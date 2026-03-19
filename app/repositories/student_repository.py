from app.models.finance import Student
from app import db


class StudentRepository:
    """
    Student repository for database operations on the Student model.
    SRP: Single responsibility - only handles Student data access.
    """
    
    @staticmethod
    def get_by_id(student_id):
        """
        Get a student by their ID.
        
        Args:
            student_id: UUID of the student
            
        Returns:
            Student object or None if not found
        """
        return Student.query.get(student_id)
    
    @staticmethod
    def get_by_admission_number(admission_number):
        """
        Get a student by their admission number.
        
        Args:
            admission_number: Admission number (unique)
            
        Returns:
            Student object or None if not found
        """
        return Student.query.filter_by(admission_number=admission_number).first()
    
    @staticmethod
    def get_by_nemis_upi(nemis_upi):
        """
        Get a student by their NEMIS UPI.
        
        Args:
            nemis_upi: NEMIS UPI (unique)
            
        Returns:
            Student object or None if not found
        """
        return Student.query.filter_by(nemis_upi=nemis_upi).first()
    
    @staticmethod
    def get_all():
        """
        Get all students.
        
        Returns:
            List of Student objects
        """
        return Student.query.all()
    
    @staticmethod
    def get_with_debt():
        """
        Get all students with outstanding balance (debt).
        
        Returns:
            List of Student objects where current_balance > 0
        """
        return Student.query.filter(Student.current_balance > 0).all()
    
    @staticmethod
    def create(admission_number, full_name, parent_phone, nemis_upi=None):
        """
        Create a new student record.
        
        Args:
            admission_number: Unique admission number
            full_name: Student's full name
            parent_phone: Parent/guardian phone number
            nemis_upi: Optional NEMIS UPI
            
        Returns:
            Created Student object
            
        Raises:
            ValueError: If admission_number already exists
        """
        # Check for duplicate admission number
        existing = Student.query.filter_by(admission_number=admission_number).first()
        if existing:
            raise ValueError(f"Student with admission number {admission_number} already exists")
        
        student = Student(
            admission_number=admission_number,
            full_name=full_name,
            parent_phone=parent_phone,
            nemis_upi=nemis_upi,
            current_balance=0.00
        )
        
        db.session.add(student)
        db.session.flush()  # Get the student.id without committing
        
        return student
    
    @staticmethod
    def update_balance(student_id, amount_change):
        """
        Update student's balance (add or subtract amount).
        
        Args:
            student_id: UUID of the student
            amount_change: Amount to add to balance (negative to subtract)
            
        Returns:
            Updated Student object or None if not found
        """
        student = Student.query.get(student_id)
        if not student:
            return None
        
        # Update the balance
        from decimal import Decimal
        student.current_balance = (student.current_balance or 0) + Decimal(str(amount_change))
        
        db.session.add(student)
        db.session.flush()
        
        return student
    
    @staticmethod
    def set_balance(student_id, new_balance):
        """
        Set student's balance to a specific amount.
        
        Args:
            student_id: UUID of the student
            new_balance: New balance amount
            
        Returns:
            Updated Student object or None if not found
        """
        student = Student.query.get(student_id)
        if not student:
            return None
        
        from decimal import Decimal
        student.current_balance = Decimal(str(new_balance))
        
        db.session.add(student)
        db.session.flush()
        
        return student
    
    @staticmethod
    def update(student_id, **kwargs):
        """
        Update student attributes.
        
        Args:
            student_id: UUID of the student
            **kwargs: Attributes to update (full_name, parent_phone, nemis_upi)
            
        Returns:
            Updated Student object or None if not found
        """
        student = Student.query.get(student_id)
        if not student:
            return None
        
        # Only allow specific fields to be updated
        allowed_fields = {'full_name', 'parent_phone', 'nemis_upi'}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(student, key, value)
        
        db.session.add(student)
        db.session.flush()
        
        return student
    
    @staticmethod
    def delete(student_id):
        """
        Delete a student record.
        
        Args:
            student_id: UUID of the student
            
        Returns:
            Boolean indicating success
        """
        student = Student.query.get(student_id)
        if not student:
            return False
        
        db.session.delete(student)
        db.session.flush()
        
        return True
    
    @staticmethod
    def count():
        """
        Count total number of students.
        
        Returns:
            Integer count of students
        """
        return Student.query.count()
    
    @staticmethod
    def count_with_debt():
        """
        Count students with outstanding balance.
        
        Returns:
            Integer count of students with debt
        """
        return Student.query.filter(Student.current_balance > 0).count()
