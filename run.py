from app import create_app, db

# Import your models here so SQLAlchemy knows they exist before creating tables
from app.models.auth import Role, User
from app.models.finance import VoteHead, Supplier, Transaction, LedgerEntry
from app.models.student import Student

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables verified and created successfully.")

    # Start the server on port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
