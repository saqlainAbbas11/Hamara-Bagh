from flask import Blueprint, Response, current_app, render_template, request, send_from_directory

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    return render_template("index.html")


@bp.route("/recommend")
def recommend_page():
    return render_template("recommend.html")


@bp.route("/plants")
def plants_page():
    return render_template("plants.html")


@bp.route("/flowers")
def flowers_page():
    return render_template("flowers.html")


@bp.route("/match")
def match_page():
    return render_template("match.html")


@bp.route("/troubleshoot")
def troubleshoot_page():
    return render_template("troubleshoot.html")


@bp.route("/calendar")
def calendar_page():
    return render_template("calendar.html")


@bp.route("/guides")
def guides_page():
    return render_template("guides.html")


@bp.route("/journal")
def journal_page():
    return render_template("journal.html")


@bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Serve journal progress photos (stored under instance/uploads)."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@bp.route("/robots.txt")
def robots_txt():
    sitemap_url = request.url_root.rstrip("/") + "/sitemap.xml"
    body = f"User-agent: *\nAllow: /\n\nSitemap: {sitemap_url}\n"
    return Response(body, mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap_xml():
    root = request.url_root.rstrip("/")
    pages = ["/", "/recommend", "/plants", "/flowers", "/match", "/calendar", "/guides", "/troubleshoot", "/journal"]
    entries = "".join(
        f"<url><loc>{root}{path}</loc><changefreq>weekly</changefreq></url>" for path in pages
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f"{entries}</urlset>")
    return Response(xml, mimetype="application/xml")
