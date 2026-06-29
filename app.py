from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    Response
)
import json  # lets us read and write JSON files
import os  # lets us work with file paths
import re  # lets us check text patterns (like usernames and passwords)
import csv  # lets us build CSV files
import io  # lets us build the CSV file in memory before sending it
from werkzeug.security import generate_password_hash, check_password_hash  # tools to safely hash and check passwords

app = Flask(__name__)  # create the Flask app

# Secret key for sessions (you can change this string)
app.secret_key = "change-this-secret-key-later"

# ---------- Paths ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # the folder this file lives in
DATA_DIR = os.path.join(BASE_DIR, "data")  # the folder where our data files live
BUSINESSES_FILE = os.path.join(DATA_DIR, "businesses.json")  # file with all the business info
REVIEWS_FILE = os.path.join(DATA_DIR, "reviews.json")  # file with all the reviews
USERS_FILE = os.path.join(DATA_DIR, "users.json")  # file with all the user accounts
COUPONS_FILE = os.path.join(DATA_DIR, "coupons.json")  # file with all the coupons

# ---------- Helper functions ----------

def load_json(path, default):
    """Load JSON from a file, or return default if file is missing/broken."""
    if not os.path.exists(path):  # if the file doesn't exist yet
        return default  # just give back the default value
    with open(path, "r", encoding="utf-8") as f:  # open the file to read it
        try:
            return json.load(f)  # try to read the JSON data
        except json.JSONDecodeError:  # if the file is broken/empty
            return default  # give back the default value instead


def save_json(path, data):
    """Save JSON to a file with pretty formatting."""
    with open(path, "w", encoding="utf-8") as f:  # open the file to write to it
        json.dump(data, f, indent=2)  # write the data nicely formatted


# Make current_user available in all templates
@app.context_processor
def inject_user():
    return {"current_user": session.get("user")}  # share the logged-in user with every page


# ---------- AUTH ROUTES (Sign up / Login / Logout) ----------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    users = load_json(USERS_FILE, [])  # get the list of existing users

    if request.method == "POST":  # if the user submitted the sign up form
        username = request.form.get("username", "").strip()  # get the typed username
        password = request.form.get("password", "").strip()  # get the typed password
        confirm = request.form.get("confirm", "").strip()  # get the typed confirm password

        # basic validation
        if not username or not password:  # if either box was left empty
            error = "Username and password are required."
            return render_template("signup.html", error=error, username=username)  # keep username so they don't retype it

        if not re.match(r"^[A-Za-z0-9_]{3,20}$", username):  # check username only has letters/numbers/underscores
            error = (
                "Username must be 3-20 characters and may only contain "
                "letters, numbers, and underscores."
            )
            return render_template("signup.html", error=error, username=username)  # keep username so they don't retype it

        if (
            len(password) < 8  # password too short
            or not re.search(r"[A-Z]", password)  # missing a capital letter
            or not re.search(r"[a-z]", password)  # missing a lowercase letter
            or not re.search(r"\d", password)  # missing a number
        ):
            error = (
                "Password must be at least 8 characters long and contain "
                "at least one uppercase letter, one lowercase letter, and one number."
            )
            return render_template("signup.html", error=error, username=username)  # keep username, only password boxes get cleared

        if password != confirm:  # if the two password boxes don't match
            error = "Passwords do not match."
            return render_template("signup.html", error=error, username=username)  # keep username so they don't retype it

        # check if username already exists
        for u in users:
            if u["username"].lower() == username.lower():  # compare names without caring about uppercase/lowercase
                error = "That username is already taken."
                return render_template("signup.html", error=error, username=username)  # keep username so they don't retype it

        # ✅ store pending user in session, but DON'T save to users.json yet
        session["pending_signup"] = {
            "username": username,
            "password_hash": generate_password_hash(password),  # turn the password into a safe scrambled version
        }

        # go to the maze step
        return redirect(url_for("signup_maze"))

    # GET
    return render_template("signup.html")  # just show the empty sign up form

@app.route("/signup-maze", methods=["GET", "POST"])
def signup_maze():
    # must have a pending signup stored from /signup
    pending = session.get("pending_signup")  # check if they actually went through the signup form first
    if not pending:  # if not, send them back to sign up
        return redirect(url_for("signup"))

    error = None

    if request.method == "POST":  # if they submitted the maze/captcha
        captcha_ok = request.form.get("captcha_ok", "0")  # check if they solved the maze

        if captcha_ok != "1":  # if they didn't pass the maze
            error = "Please complete the cheese maze to prove you're not a bot."
        else:
            # ✅ now we actually create the user
            users = load_json(USERS_FILE, [])  # get the current list of users
            users.append({
                "username": pending["username"],
                "password_hash": pending["password_hash"],
                "favorites": []  # new user starts with no favorite businesses
            })
            save_json(USERS_FILE, users)  # save the new user to the file

            # log them in and clear pending signup
            session["user"] = pending["username"]  # mark them as logged in
            session.pop("pending_signup", None)  # remove the temporary signup info

            return redirect(url_for("home"))

    return render_template("signup_maze.html", error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    users = load_json(USERS_FILE, [])  # get the list of existing users

    if request.method == "POST":  # if the user submitted the login form
        username = request.form.get("username", "").strip()  # get the typed username
        password = request.form.get("password", "").strip()  # get the typed password

        # find user
        user = next((u for u in users if u["username"].lower() == username.lower()), None)  # try to find a matching account
        if not user or not check_password_hash(user["password_hash"], password):  # if no account or wrong password
            error = "Invalid username or password."
            return render_template("login.html", error=error)

        session["user"] = user["username"]  # mark them as logged in
        return redirect(url_for("home"))

    return render_template("login.html")  # just show the empty login form


@app.route("/logout")
def logout():
    session.pop("user", None)  # remove them from the logged in session
    return redirect(url_for("index"))


# ---------- MAIN APP ROUTES ----------

@app.route("/")
def index():
    """Splash / home page."""
    return render_template("index.html")


@app.route("/discover")
def discover():
    """Show list of businesses with sorting and filtering."""
    businesses = load_json(BUSINESSES_FILE, [])  # get all the businesses

    sort_by = request.args.get("sort", "name")  # how should we sort them
    category_filter = request.args.get("category", "all")  # only show one category, or all
    favorites_only = request.args.get("favorites", "no")  # only show favorites or not


    if category_filter != "all":  # if they picked a specific category
        businesses = [b for b in businesses if b.get("category") == category_filter]  # keep only that category

    if favorites_only == "yes":  # if they only want favorites
        businesses = [b for b in businesses if b.get("favorite")]  # keep only favorited businesses

    if sort_by == "rating":  # sort by rating, best first
        businesses = sorted(
            businesses,
            key=lambda b: b.get("avg_rating", 0),
            reverse=True,
        )
    elif sort_by == "category":  # sort alphabetically by category
        businesses = sorted(businesses, key=lambda b: b.get("category", ""))
    else:  # default: sort alphabetically by name
        businesses = sorted(businesses, key=lambda b: b.get("name", ""))

    all_businesses = load_json(BUSINESSES_FILE, [])  # load the full list again so filters don't affect the category list
    categories = sorted({b.get("category", "") for b in all_businesses})  # get every unique category name

    return render_template(
        "discover.html",
        businesses=businesses,
        sort_by=sort_by,
        category_filter=category_filter,
        categories=categories,
        favorites_only=favorites_only,
    )


@app.route("/discover/download-csv")
def download_csv():
    """Build a CSV report of all businesses and send it as a file download."""
    businesses = load_json(BUSINESSES_FILE, [])  # get all the businesses

    output = io.StringIO()  # a text buffer to build the CSV in memory
    writer = csv.writer(output)

    # header row
    writer.writerow([
        "ID",
        "Name",
        "Category",
        "Description",
        "Average Rating",
        "Number of Ratings",
        "Favorite",
    ])

    # one row per business
    for b in businesses:
        writer.writerow([
            b.get("id", ""),
            b.get("name", ""),
            b.get("category", ""),
            b.get("description", ""),
            b.get("avg_rating", ""),
            b.get("ratings_count", ""),
            "Yes" if b.get("favorite") else "No",
        ])

    csv_data = output.getvalue()

    # send it back as a downloadable CSV file
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=business_report.csv"},
    )


@app.route("/business/<int:biz_id>", methods=["GET", "POST"])
def business_detail(biz_id):
    """Show one business, its reviews, and let user submit a new cheese rating."""
    businesses = load_json(BUSINESSES_FILE, [])  # get all businesses
    reviews = load_json(REVIEWS_FILE, [])  # get all reviews

    # Find the business
    biz = next((b for b in businesses if int(b["id"]) == int(biz_id)), None)  # find the one business we want
    if not biz:  # if it doesn't exist
        return "Business not found", 404

    if request.method == "POST":  # if the user is submitting a review
        rating_str = request.form.get("rating", "").strip()  # get the star rating they typed
        comment = request.form.get("comment", "").strip()  # get their comment

        if len(comment) > 300:  # comment is too long
            return "Review comment must be 300 characters or less.", 400

        if not session.get("user"):  # they must be logged in to leave a review
            return redirect(url_for("login"))

        user_name = session["user"]  # who is leaving this review

        try:
            rating = int(rating_str)  # turn the rating into a number
        except ValueError:  # if it wasn't a real number
            rating = 0

        if 1 <= rating <= 5:  # only save the review if the rating makes sense (1 to 5 stars)
            reviews.append(
                {
                    "business_id": str(biz_id),
                    "rating": rating,
                    "comment": comment,
                    "user": user_name,
                }
            )
            save_json(REVIEWS_FILE, reviews)  # save the new review to the file

            # Recalculate avg rating
            biz_reviews = [r for r in reviews if r["business_id"] == str(biz_id)]  # all reviews for this business
            if biz_reviews:
                avg = sum(r["rating"] for r in biz_reviews) / len(biz_reviews)  # average all the star ratings
                biz["avg_rating"] = round(avg, 2)  # save the new average
                biz["ratings_count"] = len(biz_reviews)  # save how many reviews there are now

            for i, b in enumerate(businesses):  # find this business in the full list
                if int(b["id"]) == int(biz_id):
                    businesses[i] = biz  # update it with the new rating info
                    break
            save_json(BUSINESSES_FILE, businesses)  # save the updated business list

        return redirect(url_for("business_detail", biz_id=biz_id))

    biz_reviews = [r for r in reviews if r["business_id"] == str(biz_id)]  # all reviews for this business
    avg_rating = biz.get("avg_rating", 0)  # the business's average rating
    ratings_count = biz.get("ratings_count", len(biz_reviews))  # how many ratings it has

    return render_template(
        "business.html",
        business=biz,
        reviews=biz_reviews,
        avg_rating=avg_rating,
        ratings_count=ratings_count,
    )

@app.route("/profile")
def profile():
    username = session.get("user")  # who is logged in
    if not username:  # if nobody is logged in
        return redirect(url_for("login"))

    # Load reviews + businesses so we can show business names on the profile
    reviews = load_json(REVIEWS_FILE, [])
    businesses = load_json(BUSINESSES_FILE, [])

    biz_map = {str(b["id"]): b for b in businesses}  # quick lookup from business id to business info

    # Only this user's reviews
    user_reviews = []
    for r in reviews:
        if (r.get("user", "").strip().lower() == username.strip().lower()):  # only keep reviews written by this user
            b = biz_map.get(str(r.get("business_id")))  # find the business this review is about
            user_reviews.append({
                "business_id": int(r.get("business_id")),
                "business_name": b.get("name") if b else "Unknown Business",
                "category": b.get("category") if b else None,
                "rating": r.get("rating"),
                "comment": r.get("comment", "")
            })

    total_reviews = len(user_reviews)  # how many reviews this user has written
    avg_cheese = round(sum(r["rating"] for r in user_reviews) / total_reviews, 2) if total_reviews else None  # their average rating given

    # optional: top category
    top_category = None
    if total_reviews:
        counts = {}
        for r in user_reviews:
            cat = r.get("category") or "Other"
            counts[cat] = counts.get(cat, 0) + 1  # count how many reviews per category
        top_category = max(counts, key=counts.get)  # find the category they reviewed the most

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
    """Toggle favorite for the logged-in user only."""
    businesses = load_json(BUSINESSES_FILE, [])  # get all businesses

    for b in businesses:
        if int(b["id"]) == int(biz_id):  # find the matching business
            b["favorite"] = not b.get("favorite", False)  # flip favorite on/off
            break

    save_json(BUSINESSES_FILE, businesses)  # save the updated favorite status

    next_url = request.form.get("next", url_for("discover"))  # where to send the user back to
    return redirect(next_url + f"#biz-{biz_id}")  # jump back to that business on the page

@app.route("/home")
def home():
    """Main home page with deals and coupons."""
    coupons = load_json(COUPONS_FILE, [])  # get all the coupons
    return render_template("home.html", coupons=coupons)

@app.route("/faq")
def faq():
    """FAQ page."""
    return render_template("faq.html")

if __name__ == "__main__":
    app.run(debug=True, port=5001)  # start the website running on port 5001
