"""HTML and JSON routes for the entry-checker web UI."""

from flask import Blueprint, jsonify, render_template, request

from entry_checking.webapp.lib.check_service import CheckError, run_check

bp = Blueprint("entry_checker_web", __name__)

_DEFAULT_FORM_VALUES = {
    "comp_name": "",
    "comp_date": "",
    "rv_ruleset": "newcomer",
    "rookie_max_level": "Bronze",
    "consecutive_level_limit": "2",
}


def _form_values() -> dict[str, str]:
    """Extract the current request's form fields, falling back to defaults."""
    return {key: request.form.get(key, default) for key, default in _DEFAULT_FORM_VALUES.items()}


@bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html", form_values=_DEFAULT_FORM_VALUES)

    form_values = _form_values()

    csv_file = request.files.get("entries_csv")
    if csv_file is None or not csv_file.filename:
        return render_template(
            "index.html", form_values=form_values, error="Please choose a CSV file to upload."
        )

    result = run_check(
        form_values["comp_name"],
        form_values["comp_date"],
        form_values["rv_ruleset"],
        form_values["rookie_max_level"],
        form_values["consecutive_level_limit"],
        csv_file.stream,
    )

    if isinstance(result, CheckError):
        return render_template("index.html", form_values=form_values, error=result.message)

    return render_template("index.html", form_values=form_values, report_view=result.report_view)


@bp.route("/api/check", methods=["POST"])
def api_check():
    csv_file = request.files.get("entries_csv")
    if csv_file is None or not csv_file.filename:
        return jsonify({"error": "Please choose a CSV file to upload."}), 400

    result = run_check(
        request.form.get("comp_name", ""),
        request.form.get("comp_date", ""),
        request.form.get("rv_ruleset", ""),
        request.form.get("rookie_max_level", "Bronze"),
        request.form.get("consecutive_level_limit", ""),
        csv_file.stream,
    )

    if isinstance(result, CheckError):
        return jsonify({"error": result.message}), result.status_code

    return (
        jsonify(
            {
                "split_level_notes": result.report_view.split_level_notes,
                "groups": [
                    {"subject_name": subject_name, "messages": messages}
                    for subject_name, messages in result.report_view.groups
                ],
            }
        ),
        200,
    )
