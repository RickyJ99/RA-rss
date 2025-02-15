import requests
import certifi
from bs4 import BeautifulSoup
import re
import csv
import os
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from IPython.display import Markdown, display
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()  # just for email and password

CSV_FILE = "jobs.csv"  # database saved in simple csv file
PREDOC_URL = "https://predoc.org/opportunities"
NBER_URL = "https://www.nber.org/career-resources/research-assistant-positions-not-nber"
EJM_URL = "https://econjobmarket.org/market"


#!mkdir -p sources
#!curl -L "https://predoc.org/opportunities" -o "sources/predoc.html"


def download_html(url, filename):
    """
    Downloads the HTML content from the given URL and saves it to the specified filename.
    """
    try:
        response = requests.get(url, verify=certifi.where())
        response.raise_for_status()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Downloaded HTML from {url} to {filename}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")


# Ensure the 'sources' folder exists.
os.makedirs("sources", exist_ok=True)

# Download HTML content for each source.
download_html(PREDOC_URL, "sources/predoc.html")
download_html(NBER_URL, "sources/nber.html")
download_html(EJM_URL, "sources/ejm.html")


def extract_main_field(text):
    """
    Looks for keywords in the provided text.
    Keywords: Economics, Macroeconomics, Microeconomics, Labour, Industrial Organization,
    Enterpreneurship, Healthcare, Discrimination, Finance, Public Policy.
    Returns a comma-separated string of all found keywords or "None" if none are found.
    """
    keywords = [
        "Economics",
        "Macroeconomics",
        "Microeconomics",
        "Microeconomic theory",
        "Macroeconomic theory" "Labour",
        "Industrial Organization",
        "Entrepreneurship",
        "Healthcare",
        "Discrimination",
        "Finance",
        "Public Policy",
        "Local Economic Policy",
        "Climate",
    ]

    found = []
    for keyword in keywords:
        if keyword.lower() in text.lower():
            found.append(keyword)

    if found:
        # Remove duplicates while preserving order and return as a comma-separated string.
        unique_keywords = list(dict.fromkeys(found))
        return ", ".join(unique_keywords)
    else:
        return None


def extract_program_type(text):
    """
    Analyzes the provided text (e.g., a job title or description) to determine the program type.

    Keywords used:
      - "PreDoctoral Program" if the text includes variations like "predoctoral", "predoc", etc.
      - "Post Doc" if the text includes variations like "postdoc", "post-doctoral", etc.
      - "PhD" if the text includes "phd" or "ph.d".
      - "Research Assistant" (RA) for all other cases.

    Returns:
      A string representing the program type.
    """
    # Convert the text to lowercase for case-insensitive matching. 🔍
    text_lower = text.lower()

    # Check for PreDoctoral indicators. 🎓
    if any(kw in text_lower for kw in ["predoctoral", "pre doc", "pre-doc", "predoc"]):
        return "PreDoctoral Program"

    # Check for Post Doc indicators. 📚
    elif any(
        kw in text_lower
        for kw in ["postdoc", "post doc", "post-doc", "postdoctoral", "post doctoral"]
    ):
        return "Post Doc"

    # Check for PhD indicators. 🎓
    elif "phd" in text_lower or "ph.d" in text_lower:
        return "PhD"

    # Check for Research Assistant indicators. 💼
    elif "research assistant" in text_lower or "ra" in text_lower:
        return "Research Assistant"

    # Default category is Research Assistant (RA). 🔄
    else:
        return "Research Assistant"


def scrape_predoc():
    """
    Scrapes the pre-doctoral opportunities page from the local HTML file
    and extracts job details.
    """
    jobs = []

    # Attempt to read the local HTML file. 📂
    try:
        with open("sources/predoc.html", "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        print(
            "Error reading sources/predoc.html. Please download the HTML from predoc before proceeding. 🚫"
        )
        return jobs  # Return an empty list if the file can't be read.

    # Parse the HTML content using BeautifulSoup. 🥣
    soup = BeautifulSoup(html, "html.parser")

    # Find the container holding the opportunities using a regex on the class name. 🔍
    container = soup.find("div", class_=re.compile("Opportunities"))
    if not container:
        print("No Predoc container found. 😢")
        return jobs

    # Loop over each article element within the container. 📝
    articles = container.find_all("article")
    for article in articles:
        job = {}
        job["source"] = "Predoc"  # Mark the source as 'predoc'. 🌟

        # Extract the title and link from the <h2> element. 🏷️
        h2 = article.find("h2")
        if h2:
            a_tag = h2.find("a")
            if a_tag:
                job["program_title"] = a_tag.get_text(strip=True)
                job["link"] = a_tag.get("href", "N/A").strip()
            else:
                job["program_title"] = "N/A"
                job["link"] = "N/A"
        else:
            job["program_title"] = "N/A"
            job["link"] = "N/A"

        # Extract details from the "copy" div. 🗒️
        copy_div = article.find("div", class_="copy")
        if copy_div:
            p = copy_div.find("p")
            if p:
                text = p.get_text(separator=" ", strip=True)
                # Use regex to capture specific fields from the text. 🔍
                researcher_match = re.search(
                    r"Sponsoring Researcher\(s\):\s*(.*?)\s*Sponsoring Institution:",
                    text,
                )
                institution_match = re.search(
                    r"Sponsoring Institution:\s*(.*?)\s*Fields of Research", text
                )
                fields_match = re.search(
                    r"Fields of Research\s*:\s*(.*?)\s*Deadline:", text
                )
                deadline_match = re.search(r"Deadline:\s*(.*)", text)
                job["sponsor"] = (
                    researcher_match.group(1).strip() if researcher_match else "N/A"
                )
                job["institution"] = (
                    institution_match.group(1).strip() if institution_match else "N/A"
                )
                job["fields"] = fields_match.group(1).strip() if fields_match else "N/A"
                job["deadline"] = (
                    deadline_match.group(1).strip() if deadline_match else "N/A"
                )
            else:
                job["sponsor"] = "N/A"
                job["institution"] = "N/A"
                job["fields"] = "N/A"
                job["deadline"] = "N/A"
        else:
            job["sponsor"] = "N/A"
            job["institution"] = "N/A"
            job["fields"] = "N/A"
            job["deadline"] = "N/A"

        # Add additional fields for consistency. 🛠️
        job["university"] = "N/A"
        job["program_type"] = "N/A"
        job["publication_date"] = "N/A"

        # Determine the main field by combining text from various fields. 🔑
        text_to_search = " ".join(
            [
                job.get("fields", "N/A"),
                job.get("program_title", "N/A"),
                job.get("institution", "N/A"),
            ]
        )
        job["main_field"] = extract_main_field(text_to_search)

        # Append the extracted job details to the jobs list. ✅
        jobs.append(job)

    # Return the list of all extracted job details. 📤
    return jobs


df = pd.DataFrame(scrape_predoc()).head(10).to_markdown(index=False)
display(Markdown(df))


def scrape_nber():
    """
    Scrapes the NBER research assistant positions page from a local HTML file
    and extracts job details.
    """
    jobs = []

    # Attempt to read the local HTML file. 📂
    try:
        with open("sources/nber.html", "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        print(
            "Error reading sources/nber.html. Please download the HTML from NBER before proceeding. 🚫"
        )
        return jobs  # Return an empty list if the file can't be read.

    # Parse the HTML content using BeautifulSoup. 🥣
    soup = BeautifulSoup(html, "html.parser")

    # Find the container holding the job details using its class name. 🔍
    container = soup.find("div", class_="page-header__intro-inner")
    if container:
        # Get all <p> elements inside the container. 📝
        paragraphs = container.find_all("p")
        # Skip the first three header paragraphs. ✂️
        for p in paragraphs[2:]:
            job = {}
            job["source"] = "NBER"  # Mark the source as NBER. 🌟
            parts = p.decode_contents().split("<br>")[0].split("<br/>")

            if len(parts) >= 4:
                job["program_title"] = parts[0].strip()
                job["sponsor"] = (
                    parts[1].replace("NBER Sponsoring Researcher(s):", "").strip()
                )
                job["institution"] = parts[2].replace("Institution:", "").strip()
                if (
                    len(
                        parts[3]
                        .replace("Field(s) of Research:", "")
                        .strip()
                        .split("&amp")
                    )
                    > 1
                ):
                    fields = "".join(
                        field.strip()
                        for field in parts[3]
                        .replace("Field(s) of Research:", "")
                        .strip()
                        .split("&amp")
                    )
                else:
                    fields = parts[3].replace("Field(s) of Research:", "").strip()
                if len(fields.split(";")) > 1:
                    fields = ", ".join(field.strip() for field in fields.split(";"))

                if len(fields.split(":")) > 1:
                    fields = fields.split(":")[1]
                job["fields"] = fields
                job["program_type"] = extract_program_type(job["program_title"])
                # Combine text fields (program title and university) to determine the main field. 🔑
                text_to_search = fields
                job["main_field"] = extract_main_field(text_to_search)
                # Extract the job link from the HTML in the last part. 🔗
                link_soup = BeautifulSoup(parts[4], "html.parser")
                a_tag = link_soup.find("a")
                job["link"] = a_tag["href"] if a_tag else ""
                job["deadline"] = "N/A"  # Deadline not provided. ⏰
                job["publication_date"] = "N/A"
                # Append the extracted job to our list. ✅
                jobs.append(job)
    else:
        print("NBER container not found. 😢")

    # Return the list of all extracted job details. 📤
    return jobs


df = pd.DataFrame(scrape_nber()).head(10).to_markdown(index=False)
display(Markdown(df))


def scrape_ejm():
    """
    Scrapes the Econ Job Market (EJM) page and extracts detailed job information
    from the newer HTML structure. Post-processing steps include:
      - Merging single/multiple salaries into one cell.
      - Parsing sponsor(s) from text referencing "Professors ..."
      - Removing extraneous punctuation in 'fields' (bullet '•', semicolon ';', repeated commas).
      - Replacing 'link' with the final application link (or "N/A" if missing).
      - Inheriting 'start_date' if 'Flexible' from a previous non-Flexible record.

    Returns a list of dictionaries.
    """
    EJM_URL = "https://econjobmarket.org/market"
    jobs = []

    try:
        response = requests.get(EJM_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Each job listing is typically under <div class="panel panel-info">
        panels = soup.find_all("div", class_="panel panel-info")
        for panel in panels:
            job = {}
            job["source"] = "ejm"

            # ---------- MAIN ROW (col-md-4, col-md-4, col-md-2, col-md-2) ----------
            main_row = panel.find("div", class_="row")
            if not main_row:
                continue

            cols = main_row.find_all("div", recursive=False)

            # --- FIRST COLUMN: title, location, start_date, duration ---
            if len(cols) >= 1:
                first_col = cols[0]
                title_a = first_col.find("a", id=lambda x: x and x.startswith("title-"))

                if title_a:
                    job["program_title"] = title_a.get_text(strip=True)
                    # We'll store a temporary link here; final link will become 'application_link'
                    job["temp_link"] = title_a.get("href", "").strip()
                else:
                    job["program_title"] = "N/A"
                    job["temp_link"] = ""

                col_text = first_col.get_text(separator="\n", strip=True).split("\n")
                # Often line 2 is location
                job["location"] = col_text[1].strip() if len(col_text) >= 2 else "N/A"

                job["start_date"] = "N/A"
                job["duration"] = "N/A"
                for line in col_text:
                    lower_line = line.lower()
                    if lower_line.startswith("starts"):
                        clean_line = line.replace("Starts", "").replace(".", "").strip()
                        job["start_date"] = clean_line if clean_line else "N/A"
                    elif lower_line.startswith("duration"):
                        clean_line = line.replace("Duration:", "").strip()
                        job["duration"] = clean_line if clean_line else "N/A"

            # --- SECOND COLUMN: department, university ---
            if len(cols) >= 2:
                second_col = cols[1]
                lines_2 = second_col.get_text(separator="\n", strip=True).split("\n")
                job["department"] = lines_2[0].strip() if len(lines_2) >= 1 else "N/A"
                job["university"] = lines_2[1].strip() if len(lines_2) >= 2 else "N/A"

            # --- THIRD COLUMN: program_type, fields ---
            if len(cols) >= 3:
                third_col = cols[2]
                program_text = third_col.get_text(separator="\n", strip=True).split(
                    "\n", 1
                )
                job["program_type"] = program_text[0].strip() if program_text else "N/A"

                fields_div = third_col.find("div", id=re.compile(r"cats-\d+"))
                if fields_div:
                    fields_raw = fields_div.get_text(separator=", ", strip=True)
                else:
                    fields_raw = (
                        program_text[1].strip() if len(program_text) > 1 else ""
                    )

                # Clean fields: remove bullet dots, semicolons, repeated commas
                fields_clean = re.sub(r"[•;]", "", fields_raw)
                fields_clean = re.sub(r",\s*,", ",", fields_clean)
                fields_clean = re.sub(r"\s+", " ", fields_clean).strip(" ,")
                job["fields"] = fields_clean if fields_clean else "N/A"

            # --- FOURTH COLUMN: publication_date, deadline ---
            if len(cols) >= 4:
                fourth_col = cols[3]
                spans = fourth_col.find_all("span")

                job["publication_date"] = (
                    spans[0].get_text(strip=True) if len(spans) > 0 else "N/A"
                )
                job["deadline"] = (
                    spans[1].get_text(strip=True) if len(spans) > 1 else "N/A"
                )
            else:
                job["program_type"] = job.get("program_type") or "N/A"
                job["publication_date"] = "N/A"
                job["deadline"] = "N/A"
                job["fields"] = job.get("fields") or "N/A"

            # Placeholders for collapsed info
            job["sponsor"] = "N/A"
            job["institution"] = job["university"]
            job["main_field"] = extract_main_field(job["fields"])
            job["degree_required"] = "N/A"
            job["salary_range"] = "N/A"
            job["application_link"] = "N/A"

            # ---------- COLLAPSE BLOCK (extended info) ----------
            if title_a:
                collapse_id = title_a.get("href", "")
                if collapse_id.startswith("#"):
                    collapse_div_id = collapse_id[1:]
                    collapse_div = panel.find("div", id=collapse_div_id)
                    if collapse_div:
                        # We'll parse the entire collapse text in one go
                        collapse_text = collapse_div.get_text(
                            separator="\n", strip=True
                        )

                        # Parse sponsor(s) from text with "Professors" ...
                        # We'll look for a pattern: "Professors (.*?)." or "Professor (.*?)."
                        # This is a heuristic; adjust to your content.
                        prof_match = re.search(
                            r"(?:[Pp]rofessors?\s+)(.*?)(?:\.|$)", collapse_text
                        )
                        if prof_match:
                            sponsor_str = prof_match.group(1)
                            # Replace ' and ' with comma
                            sponsor_str = sponsor_str.replace(" and ", ", ")
                            # Split by commas
                            sponsor_list = [
                                x.strip() for x in sponsor_str.split(",") if x.strip()
                            ]
                            # Re-join with commas
                            job["sponsor"] = ", ".join(sponsor_list)

                        # We'll search within <div> tags with <strong> for structured data
                        additional_divs = collapse_div.find_all("div")
                        for div_item in additional_divs:
                            strong_tag = div_item.find("strong")
                            if strong_tag:
                                label = strong_tag.get_text(strip=True).lower()
                                val = div_item.get_text(separator="\n", strip=True)
                                # remove the strong text from val
                                val = val.replace(
                                    strong_tag.get_text(strip=True), ""
                                ).strip(": \n")

                                if "degree required" in label:
                                    job["degree_required"] = val if val else "N/A"
                                elif "job start date" in label:
                                    job["start_date"] = val if val else "N/A"
                                elif "job duration" in label:
                                    job["duration"] = val if val else "N/A"
                                elif "salary" in label:
                                    # unify multiple lines for salary
                                    raw_lines = val.split("\n")
                                    unified = " ".join(
                                        x.strip() for x in raw_lines if x.strip()
                                    )
                                    job["salary_range"] = unified if unified else "N/A"

                        # Try to parse "To Apply" link
                        apply_paragraph = collapse_div.find(
                            "p", text=re.compile(r"To\s+Apply", re.IGNORECASE)
                        )
                        if apply_paragraph:
                            next_link = apply_paragraph.find_next("a", href=True)
                            if next_link:
                                job["application_link"] = next_link.get("href", "N/A")
                        else:
                            # or search any <a> with 'apply' in text
                            apply_a = collapse_div.find(
                                "a", href=True, text=re.compile(r"apply", re.IGNORECASE)
                            )
                            if apply_a:
                                job["application_link"] = apply_a.get("href", "N/A")

            jobs.append(job)

    except Exception as e:
        print("Error during EJM scraping:", e)

    # ---------- POST-PROCESSING ----------
    # (1) Replace 'link' with final 'application_link', or "N/A" if missing/'https://econjobmarket.org'
    # (2) If 'start_date' == 'Flexible', copy from the nearest preceding non-Flexible record
    for i, job in enumerate(jobs):
        # (1) link substitution
        app_link = job["application_link"]
        if (
            not app_link
            or app_link.strip() == ""
            or app_link.strip() == "https://econjobmarket.org"
        ):
            job["link"] = "N/A"
        else:
            job["link"] = app_link

        # (2) if 'start_date' is 'Flexible', inherit from previous
        sd = job.get("start_date")
        if isinstance(sd, str) and sd.lower() == "flexible":
            new_date = "N/A"
            # look upward
            for j in range(i - 1, -1, -1):
                prev_sd = jobs[j].get("start_date")
                if (
                    prev_sd
                    and isinstance(prev_sd, str)
                    and prev_sd.lower() != "flexible"
                ):
                    new_date = prev_sd
                    break
            job["start_date"] = new_date  # can be "N/A" if never found

    # Remove temp columns
    for job in jobs:
        if "temp_link" in job:
            del job["temp_link"]
        if "application_link" in job:
            del job["application_link"]

    return jobs


df = pd.DataFrame(scrape_ejm()).head(10).to_markdown(index=False)

display(Markdown(df))


def replace_none_or_empty_in_dict(d):
    """
    Returns a new dictionary where None or empty-string/whitespace
    values are replaced with 'N/A'.
    """
    new_dict = {}
    for k, v in d.items():
        if v is None or (isinstance(v, str) and v.strip() == ""):
            new_dict[k] = "N/A"
        else:
            new_dict[k] = v
    return new_dict


def replace_none_or_empty_in_list_of_dicts(records):
    """
    Takes a list of dictionaries and replaces None or empty strings in each dictionary
    with 'N/A'.
    """
    return [replace_none_or_empty_in_dict(job) for job in records]


def read_existing_jobs(csv_file):
    """
    Reads the CSV file and returns a set of row 'signatures' for all recorded jobs.
    A row signature is a frozenset of (key, value) pairs.
    If the file does not exist, returns an empty set.

    Records are considered duplicates only if *all* fields match exactly.
    """
    existing_signatures = set()

    if os.path.exists(csv_file):
        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert the row dict into a frozenset of (key, value) pairs
                # to be hashable for set membership checks.
                # This ensures that if any field differs, the record is considered new.
                row_signature = frozenset(row.items())
                existing_signatures.add(row_signature)

    return existing_signatures


def merge_ejm_and_other(ejm_jobs, other_jobs):
    """
    Merges two lists of dictionaries:
      1) ejm_jobs, which may have columns (source, program_title, location, start_date, duration, department, university, program_type, fields, publication_date, deadline, sponsor, institution, main_field, degree_required, salary_range, link)
      2) other_jobs, which may have columns (source, program_title, sponsor, institution, fields, program_type, main_field, link, deadline, publication_date)

    Returns a single list of dictionaries with all columns (17 total). Missing fields are filled with None.
    """
    # 1. Combine the two lists
    all_jobs = ejm_jobs + other_jobs

    # 2. Identify all columns from both EJM and Other
    # (Listed explicitly here for clarity; or you can dynamically collect them from the data.)
    all_columns = {
        "source",
        "program_title",
        "location",
        "start_date",
        "duration",
        "department",
        "university",
        "program_type",
        "fields",
        "publication_date",
        "deadline",
        "sponsor",
        "institution",
        "main_field",
        "degree_required",
        "salary_range",
        "link",
    }

    # 3. Ensure each dictionary has all columns, filling missing ones with None
    for job in all_jobs:
        for col in all_columns:
            if col not in job:
                job[col] = "N\A"

    return all_jobs


def append_jobs_to_csv(csv_file, jobs, fieldnames=None):
    """
    Appends the list of job dictionaries to the CSV file.
    If the file does not exist, it is created with a header.
    If it does exist, we unify any new columns from the new jobs with the existing CSV columns.
    Then we rewrite the entire CSV with the union of all columns (no data is lost).
    """
    # 1) Read existing rows (if the file exists).
    if os.path.exists(csv_file):
        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)
    else:
        existing_rows = []

    # 2) Collect all columns from existing rows and new jobs
    existing_cols = {col for row in existing_rows for col in row.keys()}
    new_cols = {col for row in jobs for col in row.keys()}
    all_cols = existing_cols.union(new_cols)

    # 3) Fill missing columns with "N/A" for existing rows
    for row in existing_rows:
        for col in all_cols:
            if col not in row:
                row[col] = "N/A"

    # 4) Fill missing columns with "N/A" for new jobs
    for job in jobs:
        for col in all_cols:
            if col not in job:
                job[col] = "N/A"

    # 5) Merge the old and new rows
    merged_data = existing_rows + jobs

    # 6) Write the entire CSV back (overwrite) with the union of all columns
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_cols))
        writer.writeheader()
        for row in merged_data:
            writer.writerow(row)


def send_email_new_jobs(
    new_jobs,
    sender_email,
    sender_password,
    receiver_email,
    smtp_server="smtp.gmail.com",
    smtp_port=587,
):
    """
    Sends an email with new job records.

    If there is a single record, the email subject is set to the university name from that record.
    If there are multiple records, the subject lists the unique university names (comma-separated).

    The email body is an HTML table containing one row per job record.
    Clickable hyperlinks are created for the job links.
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Extract university names from the new jobs (ignoring "N/A")
    universities = [
        str(u)
        for u in (job.get("university") for job in new_jobs)
        if u != "N/A" and u != "N/A"
    ]
    subject = ", ".join(universities) if universities else "New Research Positions"
    # Construct the HTML table for the email body
    html_body = """
    <html>
      <head>
        <style>
          table, th, td {
            border: 1px solid #ddd;
            border-collapse: collapse;
            padding: 8px;
          }
          th {
            background-color: #f2f2f2;
          }
        </style>
      </head>
      <body>
        <p>New Research Positions Found:</p>
        <table>
          <tr>
            <th>Source</th>
            <th>Program Title</th>
            <th>Link</th>
            <th>Sponsor</th>
            <th>Institution</th>
            <th>Fields</th>
            <th>Main Field</th>
            <th>Deadline</th>
            <th>University</th>
            <th>Program Type</th>
            <th>Publication Date</th>
          </tr>
    """
    for job in new_jobs:
        link = job.get("link", "")
        # Make the link clickable if available
        clickable_link = f'<a href="{link}">{link}</a>' if link else "N/A"
        html_body += f"""
          <tr>
            <td>{job.get("source", "N/A")}</td>
            <td>{job.get("program_title", "N/A")}</td>
            <td>{clickable_link}</td>
            <td>{job.get("sponsor", "N/A")}</td>
            <td>{job.get("institution", "N/A")}</td>
            <td>{job.get("fields", "N/A")}</td>
            <td>{job.get("main_field", "N/A")}</td>
            <td>{job.get("deadline", "N/A")}</td>
            <td>{job.get("university", "N/A")}</td>
            <td>{job.get("program_type", "N/A")}</td>
            <td>{job.get("publication_date", "N/A")}</td>
          </tr>
        """
    html_body += """
        </table>
      </body>
    </html>
    """

    # Create a multipart email message (plain text and HTML)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    # Plain text version as fallback
    text_body = "New Research Positions Found. Please view this email in an HTML-compatible client."

    part1 = MIMEText(text_body, "plain")
    part2 = MIMEText(html_body, "html")

    msg.attach(part1)
    msg.attach(part2)

    # Send the email via SMTP
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print("Failed to send email:", e)


def main():
    # Scrape jobs from each source into separate lists.
    predoc_jobs = scrape_predoc()  # list of dicts
    nber_jobs = scrape_nber()  # list of dicts
    ejm_jobs = scrape_ejm()  # list of dicts

    # Merge the three lists of dictionaries into a single list.
    all_jobs = merge_job_data(predoc_jobs, nber_jobs, ejm_jobs)
    all_jobs = replace_none_or_empty_in_list_of_dicts(all_jobs)

    # Check if any jobs were scraped. 🚨
    if not all_jobs:
        print("No jobs were scraped.")
        return

    # Read existing row signatures from CSV (checks all fields, not just 'link'). 📂
    existing_signatures = read_existing_jobs(CSV_FILE)

    # Filter out jobs that match an existing signature exactly. 🔍
    new_jobs = []
    for job in all_jobs:
        # Convert the job into a consistent set of (key, value) pairs,
        # ignoring "N/A" fields, for consistent signature matching.
        job_str_dict = {}
        for k, v in job.items():
            if v is None or v == "N/A":
                job_str_dict[str(k)] = "N/A"  # unify your missing val
            else:
                job_str_dict[str(k)] = str(v)
        job_signature = frozenset(job_str_dict.items())

        if job_signature not in existing_signatures:
            new_jobs.append(job)

    print(f"Found {len(new_jobs)} new job(s).")

    if new_jobs:
        # Retrieve SMTP credentials from environment variables. 🔒
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")
        receiver_email = os.getenv("SENDER_EMAIL")

        # Convert the new jobs to a Pandas DataFrame for easy visualization. 📈
        df_new = pd.DataFrame(new_jobs).head(10)
        md_table = df_new.to_markdown(index=False)

        # Merge these new records with the CSV, automatically unifying columns.
        append_jobs_to_csv(CSV_FILE, new_jobs)

        # Optionally send email notifications for new records.
        # send_email_new_jobs(new_jobs, sender_email, sender_password, receiver_email)

    else:
        # If no new jobs were found, print a message and display up to 10 existing records.
        print("No new jobs found.")
        if os.path.exists(CSV_FILE):
            df_new = pd.read_csv(CSV_FILE).head(10)
            md_table = df_new.to_markdown(index=False)
        else:
            md_table = "No CSV file found."

    # Display the table in the notebook (new records or existing CSV).
    display(Markdown(md_table))


if __name__ == "__main__":
    main()
