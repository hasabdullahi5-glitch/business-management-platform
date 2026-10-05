from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


# =========================
# DATABASE
# =========================

def create_database():

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL
        )
    """)

    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            currency_code TEXT NOT NULL DEFAULT 'NGN',
            auto_detect INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO settings
        (id, currency_code, auto_detect)
        VALUES (1, 'NGN', 1)
    """)

    # Add sale date if it does not already exist
    cursor.execute("PRAGMA table_info(sales)")
    columns = cursor.fetchall()

    column_names = [column[1] for column in columns]

    if "sale_date" not in column_names:

        cursor.execute("""
            ALTER TABLE sales
            ADD COLUMN sale_date TEXT
        """)

    # Add expense date if it does not already exist
    cursor.execute("PRAGMA table_info(expenses)")
    expense_columns = cursor.fetchall()

    expense_column_names = [
        column[1] for column in expense_columns
    ]

    if "expense_date" not in expense_column_names:

        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN expense_date TEXT
        """)

    connection.commit()
    connection.close()


create_database()


# =========================
# CURRENCY
# =========================

currency_symbols = {
    "NGN": "₦",
    "USD": "$",
    "GBP": "£",
    "EUR": "€",
    "CAD": "C$",
    "AUD": "A$",
    "ZAR": "R",
    "GHS": "₵",
    "KES": "KSh",
    "AED": "د.إ",
    "INR": "₹"
}


def get_currency():

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT currency_code
        FROM settings
        WHERE id = 1
    """)

    result = cursor.fetchone()

    connection.close()

    if result:
        currency_code = result[0]
    else:
        currency_code = "NGN"

    currency_symbol = currency_symbols.get(
        currency_code,
        currency_code
    )

    return currency_code, currency_symbol


# Make currency available to every HTML page
@app.context_processor
def inject_currency():

    currency_code, currency_symbol = get_currency()

    return {
        "currency_code": currency_code,
        "currency_symbol": currency_symbol
    }


# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template("login.html")


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        connection = sqlite3.connect("business.db")
        cursor = connection.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users
                (name, email, password)
                VALUES (?, ?, ?)
                """,
                (name, email, password)
            )

            connection.commit()
            connection.close()

            # After registration, go directly to dashboard
            return redirect("/dashboard")

        except sqlite3.IntegrityError:

            connection.close()

            return "This email is already registered."

    return render_template("register.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["POST"])
def login():

    email = request.form["email"]
    password = request.form["password"]

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        AND password = ?
        """,
        (email, password)
    )

    user = cursor.fetchone()

    connection.close()

    if user:
        return get_dashboard()

    return "Invalid email or password"


# =========================
# DASHBOARD
# =========================

def get_dashboard():

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers")
    customer_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(total), 0)
        FROM sales
    """)

    total_sales = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
    """)

    total_expenses = cursor.fetchone()[0]

    cursor.execute("""
        SELECT *
        FROM products
        WHERE quantity <= 5
    """)

    low_stock_products = cursor.fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        product_count=product_count,
        customer_count=customer_count,
        total_sales=total_sales,
        total_expenses=total_expenses,
        low_stock_products=low_stock_products
    )


@app.route("/dashboard")
def dashboard():

    return get_dashboard()


# =========================
# PRODUCTS
# =========================

@app.route("/products", methods=["GET", "POST"])
def products():

    if request.method == "POST":

        name = request.form["name"]
        price = request.form["price"]
        quantity = request.form["quantity"]

        connection = sqlite3.connect("business.db")
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO products
            (name, price, quantity)
            VALUES (?, ?, ?)
            """,
            (name, price, quantity)
        )

        connection.commit()
        connection.close()

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
    """)

    products = cursor.fetchall()

    connection.close()

    return render_template(
        "products.html",
        products=products
    )


# =========================
# EDIT PRODUCT
# =========================

@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    if request.method == "POST":

        name = request.form["name"]
        price = request.form["price"]
        quantity = request.form["quantity"]

        cursor.execute(
            """
            UPDATE products
            SET name = ?, price = ?, quantity = ?
            WHERE id = ?
            """,
            (name, price, quantity, product_id)
        )

        connection.commit()
        connection.close()

        return redirect("/products")

    cursor.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    )

    product = cursor.fetchone()

    connection.close()

    return render_template(
        "edit_product.html",
        product=product
    )


# =========================
# DELETE PRODUCT
# =========================

@app.route("/delete_product/<int:product_id>")
def delete_product(product_id):

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM products
        WHERE id = ?
        """,
        (product_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/products")


# =========================
# CUSTOMERS
# =========================

@app.route("/customers", methods=["GET", "POST"])
def customers():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]

        connection = sqlite3.connect("business.db")
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO customers
            (name, email, phone)
            VALUES (?, ?, ?)
            """,
            (name, email, phone)
        )

        connection.commit()
        connection.close()

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM customers
    """)

    customers = cursor.fetchall()

    connection.close()

    return render_template(
        "customers.html",
        customers=customers
    )


# =========================
# EDIT CUSTOMER
# =========================

@app.route("/edit_customer/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]

        cursor.execute(
            """
            UPDATE customers
            SET name = ?, email = ?, phone = ?
            WHERE id = ?
            """,
            (name, email, phone, customer_id)
        )

        connection.commit()
        connection.close()

        return redirect("/customers")

    cursor.execute(
        """
        SELECT *
        FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    )

    customer = cursor.fetchone()

    connection.close()

    return render_template(
        "edit_customer.html",
        customer=customer
    )


# =========================
# DELETE CUSTOMER
# =========================

@app.route("/delete_customer/<int:customer_id>")
def delete_customer(customer_id):

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/customers")


# =========================
# SALES
# =========================

@app.route("/sales", methods=["GET", "POST"])
def sales():

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    if request.method == "POST":

        product_name = request.form["product_name"]

        quantity = int(
            request.form["quantity"]
        )

        price = float(
            request.form["price"]
        )

        cursor.execute(
            """
            SELECT id, quantity
            FROM products
            WHERE name = ?
            """,
            (product_name,)
        )

        product = cursor.fetchone()

        if product is None:

            connection.close()

            return "Product not found. Please add the product first."

        product_id = product[0]

        current_quantity = product[1]

        if quantity > current_quantity:

            connection.close()

            return "Not enough stock available."

        total = quantity * price

        cursor.execute(
            """
            INSERT INTO sales
            (product_name, quantity, price, total, sale_date)
            VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
            """,
            (
                product_name,
                quantity,
                price,
                total
            )
        )

        new_quantity = current_quantity - quantity

        cursor.execute(
            """
            UPDATE products
            SET quantity = ?
            WHERE id = ?
            """,
            (
                new_quantity,
                product_id
            )
        )

        connection.commit()

    cursor.execute("""
        SELECT *
        FROM sales
        ORDER BY id DESC
    """)

    sales = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM products
    """)

    products = cursor.fetchall()

    connection.close()

    return render_template(
        "sales.html",
        sales=sales,
        products=products
    )


# =========================
# EXPENSES
# =========================

@app.route("/expenses", methods=["GET", "POST"])
def expenses():

    if request.method == "POST":

        description = request.form["description"]

        amount = float(
            request.form["amount"]
        )

        connection = sqlite3.connect("business.db")
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO expenses
            (description, amount, expense_date)
            VALUES (?, ?, datetime('now', 'localtime'))
            """,
            (
                description,
                amount
            )
        )

        connection.commit()
        connection.close()

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM expenses
        ORDER BY id DESC
    """)

    expenses = cursor.fetchall()

    connection.close()

    return render_template(
        "expenses.html",
        expenses=expenses
    )


# =========================
# REPORTS
# =========================

@app.route("/reports")
def reports():

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(total), 0)
        FROM sales
    """)

    total_sales = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
    """)

    total_expenses = cursor.fetchone()[0]

    profit = total_sales - total_expenses

    cursor.execute("""
        SELECT COUNT(*)
        FROM products
    """)

    product_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM customers
    """)

    customer_count = cursor.fetchone()[0]

    connection.close()

    return render_template(
        "reports.html",
        total_sales=total_sales,
        total_expenses=total_expenses,
        profit=profit,
        product_count=product_count,
        customer_count=customer_count
    )


# =========================
# SETTINGS
# =========================

@app.route("/settings", methods=["GET", "POST"])
def settings():

    if request.method == "POST":

        currency_code = request.form["currency"]

        auto_detect = request.form.get(
            "auto_detect"
        )

        if auto_detect == "on":
            auto_detect_value = 1
        else:
            auto_detect_value = 0

        connection = sqlite3.connect("business.db")
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE settings
            SET currency_code = ?,
                auto_detect = ?
            WHERE id = 1
            """,
            (
                currency_code,
                auto_detect_value
            )
        )

        connection.commit()
        connection.close()

        return redirect("/settings")

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT currency_code, auto_detect
        FROM settings
        WHERE id = 1
    """)

    setting = cursor.fetchone()

    connection.close()

    return render_template(
        "settings.html",
        setting=setting,
        currency_symbols=currency_symbols
    )


# =========================
# AUTOMATIC CURRENCY DETECTION
# =========================

@app.route("/detect_currency", methods=["POST"])
def detect_currency():

    currency_code = request.form.get(
        "currency"
    )

    if currency_code not in currency_symbols:

        return "Invalid currency"

    connection = sqlite3.connect("business.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT auto_detect
        FROM settings
        WHERE id = 1
        """
    )

    setting = cursor.fetchone()

    if setting and setting[0] == 1:

        cursor.execute(
            """
            UPDATE settings
            SET currency_code = ?
            WHERE id = 1
            """,
            (currency_code,)
        )

        connection.commit()

    connection.close()

    return "OK"


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    import webbrowser
    from threading import Timer

    def open_browser():
        webbrowser.open("http://127.0.0.1:5000")

    Timer(1, open_browser).start()

    app.run(debug=True)
