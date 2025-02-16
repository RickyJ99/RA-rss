from flask import Flask, render_template, request
import xml.etree.ElementTree as ET
import os
import pandas as pd

app = Flask(__name__)

# Path to XML file
XML_FILE = "jobs.xml"


def load_jobs_from_xml():
    """Reads job entries from the XML file and returns a list of dictionaries."""
    jobs = []
    if not os.path.exists(XML_FILE):
        print("⚠️ XML file not found.")
        return []

    try:
        tree = ET.parse(XML_FILE)
        root = tree.getroot()

        for entry in root.findall("entry"):
            job = {child.tag: child.text if child.text else "N/A" for child in entry}
            jobs.append(job)

        print(f"✅ Loaded {len(jobs)} jobs from XML")
        return jobs

    except ET.ParseError as e:
        print(f"❌ Error parsing XML: {e}")
        return []


@app.route("/")
def index():
    """Renders the job listings table with filtering and sorting."""
    jobs = load_jobs_from_xml()

    # Get filter and sort parameters from the request
    search_query = request.args.get("search", "").strip().lower()
    sort_by = request.args.get("sort", "publication_date")
    order = request.args.get("order", "desc")

    # Apply filtering
    if search_query:
        jobs = [job for job in jobs if search_query in job["program_title"].lower()]

    # Convert to DataFrame for easier sorting
    df = pd.DataFrame(jobs)

    # Handle missing values
    df.replace("N/A", "", inplace=True)

    # Sort based on user selection
    ascending = order == "asc"
    if sort_by in df.columns:
        df = df.sort_values(by=[sort_by], ascending=ascending, na_position="last")

    return render_template(
        "index.html",
        jobs=df.to_dict(orient="records"),
        search_query=search_query,
        sort_by=sort_by,
        order=order,
    )


if __name__ == "__main__":
    app.run(debug=True)
