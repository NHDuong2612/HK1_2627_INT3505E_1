import sqlite3
import random

DB_NAME = "orders.db"
DUMP_NAME = "dump.sql"

# Danh sách dữ liệu mẫu
FIRST_NAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương"]
MIDDLE_NAMES = ["Văn", "Thị", "Minh", "Thành", "Đức", "Thanh", "Quốc", "Hoàng", "Ngọc", "Thảo", "Hồng", "Anh"]
LAST_NAMES = ["An", "Bình", "Cường", "Dũng", "Em", "Giang", "Hải", "Hùng", "Khanh", "Lâm", "Nam", "Phúc", "Quân", "Sơn", "Tâm", "Tuấn", "Trinh", "Vinh"]

PRODUCTS = [
    ("Sách Lập trình Python cơ bản", 120000),
    ("Sách Flask Web Development", 180000),
    ("Sách Clean Code", 250000),
    ("Sách System Design Interview", 320000),
    ("Sách Cấu trúc dữ liệu và Giải thuật", 150000),
    ("Tai nghe Bluetooth Không dây", 450000),
    ("Bàn phím cơ không dây", 1200000),
    ("Chuột máy tính Ergonomic", 350000),
    ("Màn hình máy tính 24 inch", 2800000),
    ("Sổ tay ghi chép B5", 45000),
    ("Bút ký kim loại cao cấp", 85000),
    ("Balo chống nước đựng Laptop", 390000)
]

def seed_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Tạo bảng orders
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    """)

    # 2. Sinh 100 bản ghi mẫu
    orders = []
    for _ in range(100):
        c_name = f"{random.choice(FIRST_NAMES)} {random.choice(MIDDLE_NAMES)} {random.choice(LAST_NAMES)}"
        p_name, base_price = random.choice(PRODUCTS)
        qty = random.randint(1, 5)
        # Giá ngẫu nhiên dao động một chút so với giá gốc
        price = float(base_price)

        orders.append((c_name, p_name, qty, price))

    cursor.executemany("""
        INSERT INTO orders (customer_name, product_name, quantity, price)
        VALUES (?, ?, ?, ?)
    """, orders)

    conn.commit()
    print(f"-> Đã tạo thành công {len(orders)} bản ghi vào '{DB_NAME}'.")

    # 3. Tự động xuất file dump.sql
    with open(DUMP_NAME, "w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    print(f"-> Đã xuất thành công file '{DUMP_NAME}'.")

    conn.close()

if __name__ == "__main__":
    seed_database()