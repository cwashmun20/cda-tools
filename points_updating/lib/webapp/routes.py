"""HTML routes for the points-updater web UI."""

from flask import Blueprint, render_template, request

from points_updating.lib.webapp.update_service import UpdateError, run_update

bp = Blueprint("points_updater_web", __name__)


@bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html", submitted_pairs=[("", "")], dry_run=True)

    urls = [u.strip() for u in request.form.getlist("url")]
    dates = request.form.getlist("date")
    submitted_pairs = list(zip(urls, dates)) or [("", "")]
    dry_run = "dry_run" in request.form

    # Drop rows with an empty URL - e.g. a leftover blank row from the
    # dynamic add/remove-row form - rather than erroring on them.
    pairs = [(url, d) for url, d in zip(urls, dates) if url]
    if not pairs:
        return render_template(
            "index.html",
            submitted_pairs=submitted_pairs,
            dry_run=dry_run,
            error="At least one results link is required.",
        )

    result = run_update([url for url, _ in pairs], [d for _, d in pairs], dry_run=dry_run)

    if isinstance(result, UpdateError):
        return render_template(
            "index.html", submitted_pairs=submitted_pairs, dry_run=dry_run, error=result.message
        )

    return render_template(
        "index.html",
        submitted_pairs=submitted_pairs,
        dry_run=dry_run,
        dancer_names=result.dancer_names,
        all_text=result.all_text,
        results_data={"__all__": result.all_text, **result.dancer_text},
        new_dancer_count=result.new_dancer_count,
    )
