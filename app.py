from flask import Flask, render_template, redirect, url_for, flash
from scraper import scrape_dejong_corals, load_saved_corals

app = Flask(__name__)
app.secret_key = "test-secret-key"


@app.route("/")
def index():
    corals = load_saved_corals()
    return render_template("index.html", corals=corals)


@app.route("/scrape")
def scrape():
    try:
        corals = scrape_dejong_corals()
        flash(f"Scrape klaar: {len(corals)} koralen gevonden.", "success")
    except Exception as e:
        flash(f"Scrape mislukt: {e}", "error")

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055, debug=True)
