import hashlib
import random
import sqlite3


def compute_etag(title, author, isbn, price):
    content = f"{title}:{author}:{isbn}:{price}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def generate_books_db():
    # Kết nối/Tạo file books.db
    conn = sqlite3.connect("books.db")
    cursor = conn.cursor()

    # Reset bảng nếu đã tồn tại để đảm bảo đúng 100 bản ghi mới
    cursor.execute("DROP TABLE IF EXISTS books")
    cursor.execute("""
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT NOT NULL,
            price REAL NOT NULL,
            etag TEXT
        )
    """)

    # Dữ liệu nguyên liệu sinh ngẫu nhiên
    topics = [
        "Lập trình Python",
        "Thiết kế Microservices",
        "RESTful API Thực Chiến",
        "Cấu trúc dữ liệu",
        "Giải thuật nâng cao",
        "Hệ điều hành",
        "Mạng máy tính",
        "Cơ sở dữ liệu SQLite",
        "Học máy cơ bản",
        "Trí tuệ nhân tạo",
        "Kiến trúc phần mềm",
        "Clean Code",
        "Design Patterns",
        "Docker và Kubernetes",
        "An toàn thông tin",
        "Lập trình Web với Flask",
        "Lập trình Frontend với React",
        "Tối ưu hóa thuật toán",
        "DevOps căn bản",
        "Phân tích dữ liệu",
    ]

    subtitles = [
        "Căn Bản",
        "Nâng Cao",
        "Toàn Tập",
        "Từ Khoảng Trắng Đến Chuyên Gia",
        "Thực Hành Dành Cho Developer",
        "Tập 1",
        "Tập 2",
        "Ứng Dụng Thực Tế",
        "Bí Quyết Chuyên Sâu",
        "Cẩm Nang Lập Trình Viên",
    ]

    authors = [
        "Nguyễn Văn A",
        "Trần Thị B",
        "Lê Văn C",
        "Phạm Hoàng D",
        "Hoàng Minh E",
        "John Doe",
        "Jane Smith",
        "Robert C. Martin",
        "Erich Gamma",
        "Martin Fowler",
        "Đặng Văn G",
        "Vũ Thị H",
    ]

    books_data = []

    # Sinh đúng 100 bản ghi
    for i in range(1, 101):
        topic = random.choice(topics)
        sub = random.choice(subtitles)
        title = f"{topic} - {sub} #{i}"
        author = random.choice(authors)

        # Tạo mã ISBN 13 chữ số
        isbn = f"978-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(0, 9)}"

        # Giá ngẫu nhiên từ 50,000 đến 500,000 VNĐ
        price = float(random.randint(5, 50) * 10000)

        # Tính toán etag theo đúng logic API
        etag = compute_etag(title, author, isbn, price)

        books_data.append((title, author, isbn, price, etag))

    # Chèn 100 bản ghi vào database
    cursor.executemany(
        """
        INSERT INTO books (title, author, isbn, price, etag)
        VALUES (?, ?, ?, ?, ?)
    """,
        books_data,
    )

    conn.commit()
    conn.close()
    print("-> Đã tạo thành công file 'books.db' chứa đúng 100 bản ghi!")


if __name__ == "__main__":
    generate_books_db()