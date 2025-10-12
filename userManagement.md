# User Management System - Features

## Team Contributors
- **Rindy Tuy** - Project Setup and UI
- **Oluchi Nwabuoku** - Database Setup, User Management, and Roles & Permissions
- **Rasinie Karen Seunsom** - Authentication Setup
- **Cong Duy Vuong Dao** - User Deactivation

---

## 1. Authentication (Login)

**What it does:** Users log in with their Office 365 account. No separate passwords needed.

**How it works:**
1. User clicks "Get Started" on home page
2. App redirects to Microsoft login page using MSAL
3. User enters O365 credentials at Microsoft
4. Microsoft sends back an authorization code
5. App exchanges code for access token
6. User info stored in Flask session
7. User redirected to profile page

**Key files:**
- `app/auth/routes.py` - Login logic
- `app/ui/templates/home.html` - Landing page
- `app/ui/templates/profile.html` - User profile display

---

## 2. User Management

**What it does:** Admins can view, add, edit, and remove users.

**How it works:**
1. Navigate to `/users` to see user table
2. Table displays: Name, Email, Role, Actions
3. "Add user" button opens form for new users
4. "Edit" button updates existing user info
5. "Delete" button removes users from database
6. All data stored in SQLite


**Key files:**
- `app/users/routes.py` - User CRUD operations
- `app/ui/templates/users_list.html` - User table

---

## 3. Roles & Permissions

**What it does:** Controls what users can access based on their role.

**Roles:**
- **Basic User** - View own profile only
- **Admin** - Manage all users and permissions

**How it works:**
1. Role assigned when user is created
2. Before loading pages, check user's role in session
3. Admins see all features (Add/Edit/Delete buttons)
4. Basic users only see their own profile
5. Unauthorized access returns 403 error


---

## 4. User Deactivation

**What it does:** Temporarily disable user access without deleting their account.

**How it works:**
1. Admin clicks "Deactivate" button on user row
2. User's status field updated to "inactive" in database
3. During login, system checks status field
4. If inactive, login blocked with error message
5. Inactive users appear grayed out in table
6. Admin can click "Activate" to restore access


---

## Project Structure

```
/TeamArlington
  /app
    __init__.py              # App setup, register blueprints
    /auth
      routes.py              # Login, callback, profile
    /users
      routes.py              # List, add, edit, delete, deactivate
    /ui
      /templates
        base.html            # Layout with nav bar
        home.html            # Landing page
        profile.html         # User profile
        users_list.html      # User table
      /css
        style.css            # Styling
  run.py                     # Start app
  requirements.txt           # Dependencies
```

---

## How to Run

1. Install packages: `pip install -r requirements.txt`
2. Run app: `python3 run.py`
3. Visit: `http://localhost:5000`

---

## Key Technologies

- **Flask** - Web framework for routing and templates
- **MSAL** - Microsoft authentication library
- **SQLite** - Database for user storage
- **Blueprints** - Organize routes into modules (auth, users)
- **Sessions** - Store logged-in user info
