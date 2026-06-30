from flask import (  # import flask pieces
    Flask,  # app class
    render_template,  # render html templates
    request,  # access request data
    redirect,  # redirect helper
    url_for,  # build urls for routes
    session,  # user session storage
    Response  # raw response builder
)
import json  # lets us read and write JSON files
import os  # lets us work with file paths
import re  # lets us check text patterns (like usernames and passwords)
import csv  # lets us build CSV files
import io  # lets us build the CSV file in memory before sending it
from werkzeug.security import generate_password_hash, check_password_hash  # tools to safely hash and check passwords

app = Flask(__name__)  # create the Flask app

# Secret key for sessions (you can change this string)
app.secret_key = "change-this-secret-key-later"  # secret key value

# ---------- Paths ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # the folder this file lives in
DATA_DIR = os.path.join(BASE_DIR, "data")  # the folder where our data files live
BUSINESSES_FILE = os.path.join(DATA_DIR, "businesses.json")  # file with all the business info
REVIEWS_FILE = os.path.join(DATA_DIR, "reviews.json")  # file with all the reviews
USERS_FILE = os.path.join(DATA_DIR, "users.json")  # file with all the user accounts
COUPONS_FILE = os.path.join(DATA_DIR, "coupons.json")  # file with all the coupons

# ---------- Helper functions ----------

def load_json(path, default):  # load json with fallback
    """Load JSON from a file, or return default if file is missing/broken."""
    if not os.path.exists(path):  # if the file doesn't exist yet
        return default  # just give back the default value
    with open(path, "r", encoding="utf-8") as f:  # open the file to read it
        try:  # attempt to parse
            return json.load(f)  # try to read the JSON data
        except json.JSONDecodeError:  # if the file is broken/empty
            return default  # give back the default value instead


def save_json(path, data):  # write json to file
    """Save JSON to a file with pretty formatting."""
    with open(path, "w", encoding="utf-8") as f:  # open the file to write to it
        json.dump(data, f, indent=2)  # write the data nicely formatted


def calc_rating(reviews, biz_id):  # compute avg rating and count
    """Calculate live avg rating + count for a business from its reviews."""
    biz_reviews = [r for r in reviews if r["business_id"] == str(biz_id)]  # reviews for this business
    if not biz_reviews:  # no reviews yet
        return 0, 0  # default rating and count
    avg = round(sum(r["rating"] for r in biz_reviews) / len(biz_reviews), 2)  # average rating
    return avg, len(biz_reviews)  # rating + how many reviews


MOUSE_COLORS = [  # list of selectable mouse colors
    "#c9a87c", "#8b5e3c", "#f2c94c", "#eb5757",  # color hex values
    "#2f80ed", "#27ae60", "#9b51e0", "#bdbdbd",  # more color hex values
]  # allowed mouse colors for profile customization


# Make current_user available in all templates
@app.context_processor  # register context processor
def inject_user():  # inject current user into templates
    return {"current_user": session.get("user")}  # share the logged-in user with every page


# ---------- AUTH ROUTES (Sign up / Login / Logout) ----------

@app.route("/signup", methods=["GET", "POST"])  # signup route
def signup():  # handle signup form
    users = load_json(USERS_FILE, [])  # get the list of existing users

    if request.method == "POST":  # if the user submitted the sign up form
        username = request.form.get("username", "").strip()  # get the typed username
        password = request.form.get("password", "").strip()  # get the typed password
        confirm = request.form.get("confirm", "").strip()  # get the typed confirm password

        # basic validation
        if not username or not password:  # if either box was left empty
            error = "Username and password are required."  # set error message
            return render_template("signup.html", error=error, username=username)  # keep username so they don't retype it

        if not re.match(r"^[A-Za-z0-9_]{3,20}$", username):  # check username only has letters/numbers/underscores
            error = (  # build error message
                "Username must be 3-20 characters and may only contain "  # message part 1
                "letters, numbers, and underscores."  # message part 2
            )
            return render_template("signup.html", error=error, username=username)  # keep username so they don't retype it

        if (  # check password strength
            len(password) < 8  # password too short
            or not re.search(r"[A-Z]", password)  # missing a capital letter
            or not re.search(r"[a-z]", password)  # missing a lowercase letter
            or not re.search(r"\d", password)  # missing a number
        ):
            error = (  # build error message
                "Password must be at least 8 characters long and contain "  # message part 1
                "at least one uppercase letter, one lowercase letter, and one number."  # message part 2
            )
            return render_template("signup.html", error=error, username=username)  # keep username, only password boxes get cleared

        if password != confirm:  # if the two password boxes don't match
            error = "Passwords do not match."  # set error message
            return render_template("signup.html", error=error, username=username)  # keep username so they don't retype it

        # check if username already exists
        for u in users:  # loop through existing users
            if u["username"].lower() == username.lower():  # compare names without caring about uppercase/lowercase
                error = "That username is already taken."  # set error message
                return render_template("signup.html", error=error, username=username)  # keep username so they don't retype it

        # ✅ store pending user in session, but DON'T save to users.json yet
        session["pending_signup"] = {  # stash pending signup data
            "username": username,  # store username
            "password_hash": generate_password_hash(password),  # turn the password into a safe scrambled version
        }

        # go to the maze step
        return redirect(url_for("signup_maze"))  # send user to maze step

    # GET
    return render_template("signup.html")  # just show the empty sign up form

@app.route("/signup-maze", methods=["GET", "POST"])  # signup maze route
def signup_maze():  # handle captcha maze step
    # must have a pending signup stored from /signup
    pending = session.get("pending_signup")  # check if they actually went through the signup form first
    if not pending:  # if not, send them back to sign up
        return redirect(url_for("signup"))  # redirect to signup

    error = None  # default no error

    if request.method == "POST":  # if they submitted the maze/captcha
        captcha_ok = request.form.get("captcha_ok", "0")  # check if they solved the maze

        if captcha_ok != "1":  # if they didn't pass the maze
            error = "Please complete the cheese maze to prove you're not a bot."  # set error message
        else:  # maze passed
            # ✅ now we actually create the user
            users = load_json(USERS_FILE, [])  # get the current list of users
            users.append({  # add new user record
                "username": pending["username"],  # store username
                "password_hash": pending["password_hash"],  # store hashed password
                "favorites": []  # new user starts with no favorite businesses
            })
            save_json(USERS_FILE, users)  # save the new user to the file

            # log them in and clear pending signup
            session["user"] = pending["username"]  # mark them as logged in
            session.pop("pending_signup", None)  # remove the temporary signup info

            return redirect(url_for("home"))  # go to home page

    return render_template("signup_maze.html", error=error)  # render maze page

@app.route("/login", methods=["GET", "POST"])  # login route
def login():  # handle login form
    users = load_json(USERS_FILE, [])  # get the list of existing users

    if request.method == "POST":  # if the user submitted the login form
        username = request.form.get("username", "").strip()  # get the typed username
        password = request.form.get("password", "").strip()  # get the typed password

        # find user
        user = next((u for u in users if u["username"].lower() == username.lower()), None)  # try to find a matching account
        if not user or not check_password_hash(user["password_hash"], password):  # if no account or wrong password
            error = "Invalid username or password."  # set error message
            return render_template("login.html", error=error)  # show login form with error

        session["user"] = user["username"]  # mark them as logged in
        return redirect(url_for("home"))  # go to home page

    return render_template("login.html")  # just show the empty login form


@app.route("/logout")  # logout route
def logout():  # handle logout
    session.pop("user", None)  # remove them from the logged in session
    return redirect(url_for("index"))  # send them to the index page


# ---------- MAIN APP ROUTES ----------

@app.route("/")  # root route
def index():  # handle splash page
    """Splash / home page."""
    return render_template("index.html")  # show the splash page


@app.route("/discover")  # discover route
def discover():  # handle business discovery page
    """Show list of businesses with sorting and filtering."""
    businesses = load_json(BUSINESSES_FILE, [])  # get all the businesses
    reviews = load_json(REVIEWS_FILE, [])  # get all reviews

    for b in businesses:  # attach live rating data to each business
        b["avg_rating"], b["ratings_count"] = calc_rating(reviews, b["id"])  # set rating fields

    sort_by = request.args.get("sort", "name")  # how should we sort them
    category_filter = request.args.get("category", "all")  # only show one category, or all
    favorites_only = request.args.get("favorites", "no")  # only show favorites or not


    if category_filter != "all":  # if they picked a specific category
        businesses = [b for b in businesses if b.get("category") == category_filter]  # keep only that category

    if favorites_only == "yes":  # if they only want favorites
        businesses = [b for b in businesses if b.get("favorite")]  # keep only favorited businesses

    if sort_by == "rating":  # sort by rating, best first
        businesses = sorted(  # sort businesses list
            businesses,  # list to sort
            key=lambda b: b.get("avg_rating", 0),  # sort key is rating
            reverse=True,  # highest first
        )
    elif sort_by == "category":  # sort alphabetically by category
        businesses = sorted(businesses, key=lambda b: b.get("category", ""))  # sort by category name
    else:  # default: sort alphabetically by name
        businesses = sorted(businesses, key=lambda b: b.get("name", ""))  # sort by business name

    all_businesses = load_json(BUSINESSES_FILE, [])  # load the full list again so filters don't affect the category list
    categories = sorted({b.get("category", "") for b in all_businesses})  # get every unique category name

    return render_template(  # render discover page
        "discover.html",  # template name
        businesses=businesses,  # pass businesses
        sort_by=sort_by,  # pass sort option
        category_filter=category_filter,  # pass category filter
        categories=categories,  # pass categories list
        favorites_only=favorites_only,  # pass favorites flag
    )


@app.route("/discover/download-csv")  # csv download route
def download_csv():  # handle csv export
    """Build a CSV report of all businesses and send it as a file download."""
    businesses = load_json(BUSINESSES_FILE, [])  # get all the businesses
    reviews = load_json(REVIEWS_FILE, [])  # get all reviews

    output = io.StringIO()  # a text buffer to build the CSV in memory
    writer = csv.writer(output)  # create csv writer

    # header row
    writer.writerow([  # write header row
        "ID",  # id column
        "Name",  # name column
        "Category",  # category column
        "Description",  # description column
        "Average Rating",  # rating column
        "Number of Ratings",  # ratings count column
        "Favorite",  # favorite column
    ])

    # one row per business
    for b in businesses:  # loop through businesses
        avg_rating, ratings_count = calc_rating(reviews, b["id"])  # live rating for this row
        writer.writerow([  # write data row
            b.get("id", ""),  # id value
            b.get("name", ""),  # name value
            b.get("category", ""),  # category value
            b.get("description", ""),  # description value
            avg_rating,  # rating value
            ratings_count,  # ratings count value
            "Yes" if b.get("favorite") else "No",  # favorite flag value
        ])

    csv_data = output.getvalue()  # get the csv text

    # send it back as a downloadable CSV file
    return Response(  # build response
        csv_data,  # csv content
        mimetype="text/csv",  # set mimetype
        headers={"Content-Disposition": "attachment; filename=business_report.csv"},  # force download
    )


@app.route("/business/<int:biz_id>", methods=["GET", "POST"])  # business detail route
def business_detail(biz_id):  # handle business detail page
    """Show one business, its reviews, and let user submit a new cheese rating."""
    businesses = load_json(BUSINESSES_FILE, [])  # get all businesses
    reviews = load_json(REVIEWS_FILE, [])  # get all reviews

    # Find the business
    biz = next((b for b in businesses if int(b["id"]) == int(biz_id)), None)  # find the one business we want
    if not biz:  # if it doesn't exist
        return "Business not found", 404  # return 404 response

    if request.method == "POST":  # if the user is submitting a review
        rating_str = request.form.get("rating", "").strip()  # get the star rating they typed
        comment = request.form.get("comment", "").strip()  # get their comment

        if len(comment) > 300:  # comment is too long
            return "Review comment must be 300 characters or less.", 400  # return 400 response

        if not session.get("user"):  # they must be logged in to leave a review
            return redirect(url_for("login"))  # send to login

        user_name = session["user"]  # who is leaving this review

        try:  # attempt to parse rating
            rating = int(rating_str)  # turn the rating into a number
        except ValueError:  # if it wasn't a real number
            rating = 0  # default to zero

        if 1 <= rating <= 5:  # only save the review if the rating makes sense (1 to 5 stars)
            reviews.append(  # add new review
                {
                    "business_id": str(biz_id),  # which business
                    "rating": rating,  # star rating
                    "comment": comment,  # review text
                    "user": user_name,  # who wrote it
                }
            )
            save_json(REVIEWS_FILE, reviews)  # save the new review to the file
            # rating + count are calculated live from reviews.json, nothing else to save

        return redirect(url_for("business_detail", biz_id=biz_id))  # reload the business page

    biz_reviews = [r for r in reviews if r["business_id"] == str(biz_id)]  # all reviews for this business
    avg_rating, ratings_count = calc_rating(reviews, biz_id)  # live rating + count

    return render_template(  # render business page
        "business.html",  # template name
        business=biz,  # pass business
        reviews=biz_reviews,  # pass reviews
        avg_rating=avg_rating,  # pass average rating
        ratings_count=ratings_count,  # pass ratings count
    )

@app.route("/profile")  # profile route
def profile():  # handle profile page
    username = session.get("user")  # who is logged in
    if not username:  # if nobody is logged in
        return redirect(url_for("login"))  # send to login

    # Load reviews + businesses so we can show business names on the profile
    reviews = load_json(REVIEWS_FILE, [])  # get all reviews
    businesses = load_json(BUSINESSES_FILE, [])  # get all businesses
    users = load_json(USERS_FILE, [])  # get all users so we can find this one

    user_record = next((u for u in users if u["username"] == username), None)  # this user's data
    mouse_color = user_record.get("mouse_color", MOUSE_COLORS[0]) if user_record else MOUSE_COLORS[0]  # saved color

    biz_map = {str(b["id"]): b for b in businesses}  # quick lookup from business id to business info

    # Only this user's reviews
    user_reviews = []  # list to collect this user's reviews
    for r in reviews:  # loop through all reviews
        if (r.get("user", "").strip().lower() == username.strip().lower()):  # only keep reviews written by this user
            b = biz_map.get(str(r.get("business_id")))  # find the business this review is about
            user_reviews.append({  # add formatted review
                "business_id": int(r.get("business_id")),  # business id
                "business_name": b.get("name") if b else "Unknown Business",  # business name
                "category": b.get("category") if b else None,  # business category
                "rating": r.get("rating"),  # review rating
                "comment": r.get("comment", "")  # review comment
            })

    total_reviews = len(user_reviews)  # how many reviews this user has written
    avg_cheese = round(sum(r["rating"] for r in user_reviews) / total_reviews, 2) if total_reviews else None  # their average rating given

    # optional: top category
    top_category = None  # default no top category
    if total_reviews:  # only compute if there are reviews
        counts = {}  # tally of categories
        for r in user_reviews:  # loop through user reviews
            cat = r.get("category") or "Other"  # fallback category name
            counts[cat] = counts.get(cat, 0) + 1  # count how many reviews per category
        top_category = max(counts, key=counts.get)  # find the category they reviewed the most

    return render_template(  # render profile page
        "profile.html",  # template name
        # you can pass username OR just rely on inject_user() — either works
        current_user=username,  # pass username
        user_reviews=user_reviews,  # pass user reviews
        total_reviews=total_reviews,  # pass review count
        avg_cheese=avg_cheese,  # pass average rating
        top_category=top_category,  # pass top category
        mouse_color=mouse_color,  # pass mouse color
        mouse_colors=MOUSE_COLORS,  # pass available colors
        has_sunglasses=total_reviews >= 3,  # unlocked at 3 reviews
        has_cheese_hat=total_reviews >= 5,  # unlocked at 5 reviews
    )


@app.route("/profile/mouse-color", methods=["POST"])  # mouse color update route
def update_mouse_color():  # handle mouse color change
    """Save the logged-in user's chosen mouse color."""
    username = session.get("user")  # who is logged in
    if not username:  # must be logged in
        return redirect(url_for("login"))  # send to login

    color = request.form.get("color", "")  # the color they picked
    if color in MOUSE_COLORS:  # only allow colors from our palette
        users = load_json(USERS_FILE, [])  # get all users
        for u in users:  # loop through users
            if u["username"] == username:  # find this user
                u["mouse_color"] = color  # save their pick
                break  # stop searching
        save_json(USERS_FILE, users)  # persist to file

    return redirect(url_for("profile"))  # go back to profile


@app.route("/toggle_favorite/<int:biz_id>", methods=["POST"])  # toggle favorite route
def toggle_favorite(biz_id):  # handle favorite toggle
    """Toggle favorite for the logged-in user only."""
    businesses = load_json(BUSINESSES_FILE, [])  # get all businesses

    for b in businesses:  # loop through businesses
        if int(b["id"]) == int(biz_id):  # find the matching business
            b["favorite"] = not b.get("favorite", False)  # flip favorite on/off
            break  # stop searching

    save_json(BUSINESSES_FILE, businesses)  # save the updated favorite status

    next_url = request.form.get("next", url_for("discover"))  # where to send the user back to
    return redirect(next_url + f"#biz-{biz_id}")  # jump back to that business on the page

@app.route("/home")  # home route
def home():  # handle home page
    """Main home page with deals and coupons."""
    coupons = load_json(COUPONS_FILE, [])  # get all the coupons
    return render_template("home.html", coupons=coupons)  # render home page

@app.route("/faq")  # faq route
def faq():  # handle faq page
    """FAQ page."""
    return render_template("faq.html")  # render faq page

if __name__ == "__main__":  # run only when executed directly
    app.run(debug=True, port=5001)  # start the website running on port 5001
