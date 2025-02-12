from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/ecommerce_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ----------------------------
# Database Models
# ----------------------------
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.Text)
    category = db.Column(db.Text)
    price = db.Column(db.Float)
    actual_price = db.Column(db.Float)
    discount_percentage = db.Column(db.Integer)
    rating = db.Column(db.Float)
    rating_count = db.Column(db.Integer)
    description = db.Column(db.Text)
    image_link = db.Column(db.Text)
    product_link = db.Column(db.Text)

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.String(255), primary_key=True)
    user_name = db.Column(db.Text)

class Review(db.Model):
    __tablename__ = 'reviews'
    review_id = db.Column(db.String(255), primary_key=True)
    product_id = db.Column(db.String(255), db.ForeignKey('products.id'))
    user_id = db.Column(db.String(255), db.ForeignKey('users.user_id'))
    review_title = db.Column(db.Text)
    review_content = db.Column(db.Text)

class Purchase(db.Model):
    __tablename__ = 'purchases'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('users.user_id'))
    product_id = db.Column(db.String(255), db.ForeignKey('products.id'))

# ----------------------------
# Endpoints
# ----------------------------

@app.route('/trending', methods=['GET'])
def trending_products():
    """
    Return trending products. In this simple example, we sort by rating_count (and rating)
    to approximate popularity.
    """
    products = Product.query.order_by(Product.rating_count.desc(), Product.rating.desc()).limit(10).all()
    product_list = []
    for product in products:
        product_list.append({
            'id': product.id,
            'name': product.name,
            'rating': product.rating,
            'rating_count': product.rating_count,
            'price': product.price,
            'actual_price': product.actual_price,
            'discount_percentage': product.discount_percentage,
            'image_link': product.image_link,
            'product_link': product.product_link
        })
    return jsonify(product_list)

@app.route('/bought_together/<product_id>', methods=['GET'])
def bought_together(product_id):
    """
    Given a product_id, find all users who purchased that product and then find other products
    those users bought. Return a list of the most frequently co-purchased products.
    """
    # Find all purchase events for the given product.
    purchases = Purchase.query.filter_by(product_id=product_id).all()
    user_ids = set([p.user_id for p in purchases])
    
    # Count other products purchased by these users.
    co_purchase_counts = {}
    for user_id in user_ids:
        user_purchases = Purchase.query.filter_by(user_id=user_id).all()
        for up in user_purchases:
            if up.product_id != product_id:
                co_purchase_counts[up.product_id] = co_purchase_counts.get(up.product_id, 0) + 1

    # Sort the products by co-purchase count (highest first)
    sorted_co = sorted(co_purchase_counts.items(), key=lambda x: x[1], reverse=True)
    
    recommendations = []
    for prod_id, count in sorted_co[:5]:
        product = Product.query.get(prod_id)
        if product:
            recommendations.append({
                'id': product.id,
                'name': product.name,
                'rating': product.rating,
                'rating_count': product.rating_count,
                'price': product.price,
                'actual_price': product.actual_price,
                'discount_percentage': product.discount_percentage,
                'image_link': product.image_link,
                'product_link': product.product_link,
                'co_purchase_count': count
            })
    return jsonify(recommendations)

@app.route('/user_recommend/<user_id>', methods=['GET'])
def user_recommend(user_id):
    """
    For a given user, find products purchased by similar users.
    This simple user-based collaborative filtering algorithm:
      1. Finds all products the user has bought.
      2. Finds other users who bought those products.
      3. Recommends products those similar users bought that the user hasn't bought.
    """
    # Get the set of products the user purchased.
    user_purchases = Purchase.query.filter_by(user_id=user_id).all()
    purchased_products = set([p.product_id for p in user_purchases])
    
    # Find other users who purchased these products.
    similar_users = set()
    for prod_id in purchased_products:
        prod_purchases = Purchase.query.filter_by(product_id=prod_id).all()
        for p in prod_purchases:
            if p.user_id != user_id:
                similar_users.add(p.user_id)
    
    # Count how many times products were purchased by similar users
    product_scores = {}
    for sim_user in similar_users:
        sim_user_purchases = Purchase.query.filter_by(user_id=sim_user).all()
        for p in sim_user_purchases:
            if p.product_id not in purchased_products:
                product_scores[p.product_id] = product_scores.get(p.product_id, 0) + 1

    # Sort the products by score.
    sorted_products = sorted(product_scores.items(), key=lambda x: x[1], reverse=True)
    
    recommendations = []
    for prod_id, score in sorted_products[:5]:
        product = Product.query.get(prod_id)
        if product:
            recommendations.append({
                'id': product.id,
                'name': product.name,
                'rating': product.rating,
                'rating_count': product.rating_count,
                'price': product.price,
                'actual_price': product.actual_price,
                'discount_percentage': product.discount_percentage,
                'image_link': product.image_link,
                'product_link': product.product_link,
                'score': score
            })
    return jsonify(recommendations)

# ----------------------------
# Main
# ----------------------------
if __name__ == '__main__':
    # Make sure the tables exist (or run "db.create_all()" once after models are defined)
    # db.create_all()  # Uncomment if running for the first time.
    app.run(debug=True)
