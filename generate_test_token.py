#!/usr/bin/env python3
"""
Generate a JWT token for manual testing.
Useful for testing authenticated endpoints via curl, Postman, or browser dev tools.

Usage:
    python generate_test_token.py [username] [password]
    python generate_test_token.py admin adminpass123
    python generate_test_token.py storekeeper storekeeper123
"""
import sys
from app import create_app, db
from app.models import User, Role
from flask_jwt_extended import create_access_token
import bcrypt

def generate_token(username, password):
    """Generate JWT token for a user, creating the user if needed."""
    app = create_app()
    
    with app.app_context():
        # Try to find existing user
        user = User.query.filter_by(username=username).first()
        
        if user:
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                print(f"Invalid password for user '{username}'")
                return None
            print(f"✓ Found existing user: {username}")
        else:
            # Create new user
            print(f"[INFO] User '{username}' not found. Creating...")
            
            # Get or create 'storekeeper' role
            role = Role.query.filter_by(name='storekeeper').first()
            if not role:
                role = Role(name='storekeeper', permissions='read,write,inventory')
                db.session.add(role)
                db.session.commit()
                print(f"  [OK] Created 'storekeeper' role")
            
            # Create user
            user = User(
                username=username,
                full_name=username.title(),  # e.g., 'Storekeeper'
                email=f"{username}@test.local",
                role_id=role.id,
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"[OK] Created user: {username} (role: {role.name})")
        
        # Generate token
        token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role.name}
        )
        
        print(f"\n{'='*70}")
        print(f"JWT TOKEN for {username}:")
        print(f"{'='*70}")
        print(token)
        print(f"\n[INFO] To test in browser:")
        print(f"1. Open dev console (F12) → Application → Local Storage")
        print(f"2. Create new entry:")
        print(f"   Key:   access_token")
        print(f"   Value: {token[:50]}...")
        print(f"3. Refresh the page")
        print(f"4. Try inventory operations")
        print(f"\n[INFO] To test with curl:")
        print(f"""curl -X POST http://localhost:5000/api/inventory/items \\
  -H "Authorization: Bearer {token[:30]}..." \\
  -H "Content-Type: application/json" \\
  -d '{{"item_code":"TEST","name":"Test Item","category":"Test","unit_of_measure":"pcs","reorder_level":1}}'""")
        print(f"\n[INFO] Token expires in: {app.config['JWT_TOKEN_EXPIRES']} seconds (1 hour)")
        
        return token

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python generate_test_token.py <username> [password]")
        print("Example: python generate_test_token.py storekeeper storekeeper123")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else f"{username}123"
    
    generate_token(username, password)
