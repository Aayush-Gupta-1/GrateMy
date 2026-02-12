from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secret key for sessions (you can change this string)
app.secret_key = "change-this-secret-key-later"

# ---------- Paths ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BUSINESSES_FILE = os.path.join(DATA_DIR, "businesses.json")
REVIEWS_FILE = os.path.join(DATA_DIR, "reviews.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
COUPONS_FILE = os.path.join(DATA_DIR, "coupons.json")

# ---------- Helper functions ----------

def load_json(path, default):
    """Load JSON from a file, or return default if file is missing/broken."""
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def save_json(path, data):
    """Save JSON to a file with pretty formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# Make current_user available in all templates
@app.context_processor
def inject_user():
    return {"current_user": session.get("user")}


# ---------- AUTH ROUTES (Sign up / Login / Logout) ----------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    users = load_json(USERS_FILE, [])

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

        # basic validation
        if not username or not password:
            error = "Username and password are required."
            return render_template("signup.html", error=error)

        if password != confirm:
            error = "Passwords do not match."
            return render_template("signup.html", error=error)

        # check if username already exists
        for u in users:
            if u["username"].lower() == username.lower():
                error = "That username is already taken."
                return render_template("signup.html", error=error)

        # ✅ store pending user in session, but DON'T save to users.json yet
        session["pending_signup"] = {
            "username": username,
            "password_hash": generate_password_hash(password),
        }

        # go to the maze step
        return redirect(url_for("signup_maze"))

    # GET
    return render_template("signup.html")

@app.route("/signup-maze", methods=["GET", "POST"])
def signup_maze():
    # must have a pending signup stored from /signup
    pending = session.get("pending_signup")
    if not pending:
        return redirect(url_for("signup"))

    error = None

    if request.method == "POST":
        captcha_ok = request.form.get("captcha_ok", "0")

        if captcha_ok != "1":
            error = "Please complete the cheese maze to prove you're not a bot."
        else:
            # ✅ now we actually create the user
            users = load_json(USERS_FILE, [])
            users.append({
                "username": pending["username"],
                "password_hash": pending["password_hash"],
            })
            save_json(USERS_FILE, users)

            # log them in and clear pending signup
            session["user"] = pending["username"]
            session.pop("pending_signup", None)

            return redirect(url_for("home"))

    return render_template("signup_maze.html", error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    users = load_json(USERS_FILE, [])

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # find user
        user = next((u for u in users if u["username"].lower() == username.lower()), None)
        if not user or not check_password_hash(user["password_hash"], password):
            error = "Invalid username or password."
            return render_template("login.html", error=error)

        session["user"] = user["username"]
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))


# ---------- MAIN APP ROUTES ----------

@app.route("/")
def index():
    """Splash / home page."""
    return render_template("index.html")


@app.route("/discover")
def discover():
    """Show list of businesses with sorting and filtering."""
    businesses = load_json(BUSINESSES_FILE, [])

    sort_by = request.args.get("sort", "name")
    category_filter = request.args.get("category", "all")
    favorites_only = request.args.get("favorites", "no")

    # Filter by category
    if category_filter != "all":
        businesses = [b for b in businesses if b.get("category") == category_filter]

    # Filter favorites
    if favorites_only == "yes":
        businesses = [b for b in businesses if b.get("favorite")]

    # Sorting
    if sort_by == "rating":
        businesses = sorted(
            businesses,
            key=lambda b: b.get("avg_rating", 0),
            reverse=True,
        )
    elif sort_by == "category":
        businesses = sorted(businesses, key=lambda b: b.get("category", ""))
    else:
        businesses = sorted(businesses, key=lambda b: b.get("name", ""))

    # Build list of categories for dropdown
    all_businesses = load_json(BUSINESSES_FILE, [])
    categories = sorted({b.get("category", "") for b in all_businesses})

    return render_template(
        "discover.html",
        businesses=businesses,
        sort_by=sort_by,
        category_filter=category_filter,
        categories=categories,
        favorites_only=favorites_only,
    )


@app.route("/business/<int:biz_id>", methods=["GET", "POST"])
def business_detail(biz_id):
    """Show one business, its reviews, and let user submit a new cheese rating."""
    businesses = load_json(BUSINESSES_FILE, [])
    reviews = load_json(REVIEWS_FILE, [])

    # Find the business
    biz = next((b for b in businesses if int(b["id"]) == int(biz_id)), None)
    if not biz:
        return "Business not found", 404

    if request.method == "POST":
        rating_str = request.form.get("rating", "").strip()
        comment = request.form.get("comment", "").strip()
        user_name = request.form.get("user", "").strip()

        # If logged-in, default name to username
        if not user_name and session.get("user"):
            user_name = session["user"]
        if not user_name:
            user_name = "Anonymous"

        try:
            rating = int(rating_str)
        except ValueError:
            rating = 0

        if 1 <= rating <= 5:
            reviews.append(
                {
                    "business_id": str(biz_id),
                    "rating": rating,
                    "comment": comment,
                    "user": user_name,
                }
            )
            save_json(REVIEWS_FILE, reviews)

            # Recalculate avg rating
            biz_reviews = [r for r in reviews if r["business_id"] == str(biz_id)]
            if biz_reviews:
                avg = sum(r["rating"] for r in biz_reviews) / len(biz_reviews)
                biz["avg_rating"] = round(avg, 2)
                biz["ratings_count"] = len(biz_reviews)

            for i, b in enumerate(businesses):
                if int(b["id"]) == int(biz_id):
                    businesses[i] = biz
                    break
            save_json(BUSINESSES_FILE, businesses)

        return redirect(url_for("business_detail", biz_id=biz_id))

    biz_reviews = [r for r in reviews if r["business_id"] == str(biz_id)]
    avg_rating = biz.get("avg_rating", 0)
    ratings_count = biz.get("ratings_count", len(biz_reviews))

    return render_template(
        "business.html",
        business=biz,
        reviews=biz_reviews,
        avg_rating=avg_rating,
        ratings_count=ratings_count,
    )

@app.route("/profile")
def profile():
    username = session.get("user")
    if not username:
        return redirect(url_for("login"))

    # Load reviews + businesses so we can show business names on the profile
    reviews = load_json(REVIEWS_FILE, [])
    businesses = load_json(BUSINESSES_FILE, [])

    biz_map = {str(b["id"]): b for b in businesses}

    # Only this user's reviews
    user_reviews = []
    for r in reviews:
        if (r.get("user", "").strip().lower() == username.strip().lower()):
            b = biz_map.get(str(r.get("business_id")))
            user_reviews.append({
                "business_id": int(r.get("business_id")),
                "business_name": b.get("name") if b else "Unknown Business",
                "category": b.get("category") if b else None,
                "rating": r.get("rating"),
                "comment": r.get("comment", "")
            })

    total_reviews = len(user_reviews)
    avg_cheese = round(sum(r["rating"] for r in user_reviews) / total_reviews, 2) if total_reviews else None

    # optional: top category
    top_category = None
    if total_reviews:
        counts = {}
        for r in user_reviews:
            cat = r.get("category") or "Other"
            counts[cat] = counts.get(cat, 0) + 1
        top_category = max(counts, key=counts.get)

    return render_template(
        "profile.html",
        # you can pass username OR just rely on inject_user() — either works
        current_user=username,
        user_reviews=user_reviews,
        total_reviews=total_reviews,
        avg_cheese=avg_cheese,
        top_category=top_category
    )


@app.route("/toggle_favorite/<int:biz_id>", methods=["POST"])
def toggle_favorite(biz_id):
    """Toggle the 'favorite' flag for a business."""
    businesses = load_json(BUSINESSES_FILE, [])
    for b in businesses:
        if int(b["id"]) == int(biz_id):
            b["favorite"] = not b.get("favorite", False)
            break
    save_json(BUSINESSES_FILE, businesses)

    # Keep scroll position by redirecting back with anchor
    next_url = request.form.get("next", url_for("discover"))

    # Add fragment to maintain scroll position
    return redirect(next_url + f"#biz-{biz_id}")

@app.route("/home")
def home():
    """Main home page with deals and coupons."""
    coupons = load_json(COUPONS_FILE, [])
    return render_template("home.html", coupons=coupons)

@app.route("/faq")
def faq():
    """FAQ page."""
    return render_template("faq.html")

if __name__ == "__main__":
    app.run(debug=True, port=5001)
