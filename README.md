# emailmarketing

## endpoints
- For trending products: ```http://127.0.0.1:5000/trending```
- For bought together (replace <product_id> with an actual product id):
```http://127.0.0.1:5000/bought_together/B08HDJ86NZ```
- For user recommendations (replace <user_id> with an actual user id):
```http://127.0.0.1:5000/user_recommend/AEWAZDZZJLQUYVOVGBEUKSLXHQ5A```

### Endpoints (Explanation)
Trending Products (/trending)
– This endpoint queries the products table sorted by rating_count (and then rating) and returns the top 10.
– You can adjust the logic to factor in “trending” signals (e.g. discount percentage, recency if you add timestamps, etc.).

Frequently Bought Together (/bought_together/<product_id>)
– Given a product id, the code first finds all users who purchased that product (using the purchases table).
– It then counts other products bought by these users.
– The result is a sorted list of co‑purchased products (you can adjust how many you return).

User-based Recommendations (/user_recommend/<user_id>)
– This endpoint gathers all products purchased by a user, then finds “similar” users (users who have purchased any of these products).
– Next, it collects the products purchased by those similar users that the original user hasn’t purchased and ranks them by frequency.
– The top few recommendations are returned.

## daatabase schema and setup
create a database:
```
CREATE DATABASE ecommerce_db;
USE ecommerce_db;
```

Products table:
```
CREATE TABLE products (
    id VARCHAR(255) PRIMARY KEY,
    name TEXT,
    category TEXT,
    price DECIMAL(10,2),
    actual_price DECIMAL(10,2),
    discount_percentage INT,
    rating DECIMAL(3,1),
    rating_count INT,
    description TEXT,
    image_link TEXT,
    product_link TEXT
);
```

Users Table:
```
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    user_name TEXT
);
```

Reviews Table:
```
CREATE TABLE reviews (
    review_id VARCHAR(255) PRIMARY KEY,
    product_id VARCHAR(255),
    user_id VARCHAR(255),
    review_title TEXT,
    review_content TEXT,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

Purchases Table:
```
CREATE TABLE purchases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255),
    product_id VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

### requirements
```pip install Flask flask_sqlalchemy pymysql```