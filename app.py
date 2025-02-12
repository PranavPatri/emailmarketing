import os
from flask import Flask, request, render_template, redirect, url_for, session, flash
import pandas as pd
import numpy as np
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import euclidean_distances
from dotenv import load_dotenv
import requests

# Load environment variables from .env
load_dotenv()
MAILCHIMP_API_KEY = os.getenv("MAILCHIMP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Flask
app = Flask(__name__)
app.secret_key = 'super_secret_key'  # (In production, store this securely as well)

# =======================
# LOAD & PREPROCESS DATA
# =======================

# Load the CSV dataset
df = pd.read_csv('data.csv')

# --- Trending Products ---
# Compute a trending score for each product.
def compute_trending_score(row):
    # Assume the user_id field may contain comma separated values.
    user_ids = str(row['user_id']).split(',')
    user_count = len([uid for uid in user_ids if uid.strip() != ''])
    # For example, score can be computed as rating * rating_count * user_count.
    return row['rating'] * row['rating_count'] * user_count

df['trending_score'] = df.apply(compute_trending_score, axis=1)
trending_products = df.sort_values(by='trending_score', ascending=False)

# --- TF-IDF for Product Descriptions ---
tfidf_vectorizer = TfidfVectorizer(stop_words='english')
# Fill missing descriptions with empty strings
tfidf_matrix = tfidf_vectorizer.fit_transform(df['description'].fillna(''))

# --- Build User Purchase History for Clustering ---
# We create a dictionary mapping each user_id to a list of (category, price) tuples.
user_purchases = {}
for idx, row in df.iterrows():
    # In case there are multiple user ids (comma separated)
    user_ids = str(row['user_id']).split(',')
    for uid in user_ids:
        uid = uid.strip()
        if uid:
            if uid not in user_purchases:
                user_purchases[uid] = []
            try:
                price = float(row['price'])
            except Exception:
                price = 0.0
            user_purchases[uid].append((row['category'], price))

# For each user, choose the category they bought most often and compute the average price for that category.
user_features = []
user_ids_list = []
for uid, purchases in user_purchases.items():
    categories = [p[0] for p in purchases]
    category_counter = Counter(categories)
    main_category = category_counter.most_common(1)[0][0]
    prices = [price for cat, price in purchases if cat == main_category]
    avg_price = np.mean(prices) if prices else 0.0
    user_features.append([main_category, avg_price])
    user_ids_list.append(uid)

# Encode the categorical feature (category) to a numeric value.
le = LabelEncoder()
categories_encoded = le.fit_transform([uf[0] for uf in user_features])
user_features_numeric = np.column_stack((categories_encoded, [uf[1] for uf in user_features]))

# Run KMeans clustering on the (category, avg_price) features.
if len(user_features_numeric) > 0:
    kmeans = KMeans(n_clusters=3, random_state=42)
    user_clusters = kmeans.fit_predict(user_features_numeric)
    # Build a mapping of user_id to cluster label.
    user_cluster_mapping = {uid: cluster for uid, cluster in zip(user_ids_list, user_clusters)}
else:
    user_cluster_mapping = {}

# =======================
# IN-MEMORY USER DATABASE
# =======================
# In a production app, use a persistent database.
users_db = {}  # Format: { username: { 'password': ..., 'email': ..., 'id': ... } }

# =======================
# HELPER FUNCTIONS
# =======================

def send_email_mailchimp(recipient, subject, content):
    """
    Simulate sending an email using the Mailchimp API.
    (Replace the print statement with an actual API call using requests.)
    """
    print(f"Sending email to {recipient}:\nSubject: {subject}\nContent:\n{content}\n")
    # Example (pseudo‑code):
    # url = "https://<dc>.api.mailchimp.com/3.0/messages/send"
    # headers = {"Authorization": f"apikey {MAILCHIMP_API_KEY}"}
    # data = { ... }  # Build your payload
    # response = requests.post(url, json=data, headers=headers)
    # return response

def generate_email_template(recommendations, template_type):
    """
    Simulate generating an email template via the Gemini API.
    (In a real application, call the Gemini API using your GEMINI_API_KEY.)
    """
    content = f"--- {template_type.upper()} EMAIL TEMPLATE ---\n"
    content += "Here are your recommendations:\n"
    for rec in recommendations:
        content += f"- {rec}\n"
    return content

def get_trending_products():
    """
    Return a list of strings for the top 10 trending products.
    """
    top10 = trending_products.head(10)
    recommendations = []
    for _, row in top10.iterrows():
        rec = f"{row['name']} | {row['category']} | Price: {row['price']}"
        recommendations.append(rec)
    return recommendations

def get_addon_recommendations(product_id):
    """
    For a given product_id, find the two closest (by Euclidean distance in TF-IDF space)
    product descriptions (excluding itself) to recommend as add‑ons.
    """
    product_idx_list = df.index[df['id'] == product_id].tolist()
    if not product_idx_list:
        return []
    product_idx = product_idx_list[0]
    product_vec = tfidf_matrix[product_idx]
    distances = euclidean_distances(product_vec, tfidf_matrix)
    # Exclude the product itself by setting its distance to infinity.
    distances[0, product_idx] = np.inf
    closest_indices = distances[0].argsort()[:2]
    recommendations = []
    for idx in closest_indices:
        row = df.iloc[idx]
        rec = f"{row['name']} | {row['category']} | Price: {row['price']}"
        recommendations.append(rec)
    return recommendations

def get_weekly_recommendations(user_id):
    """
    Based on the user’s cluster (from KMeans) return the top 10 product recommendations.
    Here we simply gather products from the same category as those purchased by users in the same cluster.
    """
    if user_id not in user_cluster_mapping:
        return []
    cluster = user_cluster_mapping[user_id]
    # Find all users in the same cluster.
    same_cluster_users = [uid for uid, clus in user_cluster_mapping.items() if clus == cluster]
    product_scores = {}
    # For every user in the same cluster, add trending scores for products matching their purchased category.
    for uid in same_cluster_users:
        if uid in user_purchases:
            for cat, _ in user_purchases[uid]:
                matching_products = df[df['category'] == cat]
                for _, row in matching_products.iterrows():
                    pid = row['id']
                    product_scores[pid] = product_scores.get(pid, 0) + row['trending_score']
    # Sort by score and pick top 10.
    sorted_products = sorted(product_scores.items(), key=lambda x: x[1], reverse=True)
    recommendations = []
    for i, (pid, _) in enumerate(sorted_products):
        if i >= 10:
            break
        row = df[df['id'] == pid].iloc[0]
        rec = f"{row['name']} | {row['category']} | Price: {row['price']}"
        recommendations.append(rec)
    return recommendations

# =======================
# FLASK ROUTES
# =======================

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- Signup Page ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        email = request.form.get('email').strip()
        if username in users_db:
            flash('Username already exists. Please choose another.')
            return redirect(url_for('signup'))
        # Save user info (using the username as the unique id)
        users_db[username] = {'password': password, 'email': email, 'id': username}
        # Send email with top 10 trending products.
        trending = get_trending_products()
        email_content = generate_email_template(trending, 'signup')
        send_email_mailchimp(email, "Welcome! Here Are the Top Trending Products", email_content)
        flash('Signup successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

# --- Login Page ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        if username in users_db and users_db[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('home'))
        flash('Invalid credentials. Please try again.')
        return redirect(url_for('login'))
    return render_template('login.html')

# --- Home Page (Displays 20 products) ---
@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    # For simplicity, we display the first 20 products.
    products = df.head(20).to_dict('records')
    return render_template('home.html', products=products)

# --- Buy Route (Triggered when user clicks the "Buy" button) ---
@app.route('/buy/<product_id>')
def buy(product_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    user = users_db[username]
    # Get 2 add-on recommendations based on the product description.
    addons = get_addon_recommendations(product_id)
    email_content = generate_email_template(addons, 'buy')
    send_email_mailchimp(user['email'], "Add-on Product Recommendations", email_content)
    flash('Purchase successful! We have sent add-on recommendations to your email.')
    return redirect(url_for('home'))

# --- Logout Route ---
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# --- Simulated Weekly Email Update Route ---
@app.route('/send_weekly')
def send_weekly():
    """
    In production you’d schedule this route (or use a background task scheduler)
    to run weekly. For now, this route sends weekly recommendations to all users.
    """
    for username, user in users_db.items():
        recommendations = get_weekly_recommendations(user['id'])
        email_content = generate_email_template(recommendations, 'weekly')
        send_email_mailchimp(user['email'], "Your Weekly Product Recommendations", email_content)
    return "Weekly emails sent!"

# =======================
# RUN THE APP
# =======================
if __name__ == '__main__':
    app.run(debug=True)
