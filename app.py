from flask import Flask, render_template, redirect, url_for, flash, request
from scraper import scrape_dejong_corals, load_saved_corals, SCRAPE_SOURCES

app = Flask(__name__)
app.secret_key = "test-secret-key"


@app.route("/")
def index():
    corals = load_saved_corals()

    selected_source = request.args.get("source", "wysiwyg")
    custom_url = request.args.get("url", "")

    return render_template(
        "index.html",
        corals=corals,
        sources=SCRAPE_SOURCES,
        selected_source=selected_source,
        custom_url=custom_url
    )


@app.route("/scrape")
def scrape():
    source = request.args.get("source", "wysiwyg")
    custom_url = request.args.get("url", "").strip()

    try:
        corals = scrape_dejong_corals(
            source_key=source,
            custom_url=custom_url
        )

        flash(
            f"Scrape klaar: {len(corals)} beschikbare koralen gevonden.",
            "success"
        )

    except Exception as e:
        flash(f"Scrape mislukt: {e}", "error")

    return redirect(url_for("index", source=source, url=custom_url))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055, debug=True)
