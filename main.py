# %% [markdown]
# # Web scraping to generate RSS feed for new positions in economics
# This application is using three main sources to retrieve information about the new job posts:
# 1. [NBER](https://www.nber.org/career-resources/research-assistant-positions-not-nber)
# 2. [Predoc](https://predoc.org/opportunities)
# 3. [EconJobMarket](https://econjobmarket.org/market)
#
# The packeges that are needed are **requests**, **beautifulsoup4**,**MIMEtext**. As a first step we recall them:
#

# %%
import xml.etree.ElementTree as ET  # For XML handling
import requests  # For HTTP requests
import certifi  # For SSL certification verification
from bs4 import BeautifulSoup  # For web scraping
import re  # For regular expressions
import os  # For file and environment variable management
import pandas as pd  # For data manipulation
import smtplib  # For sending emails
from email.mime.text import MIMEText  # For constructing email messages
from email.mime.multipart import MIMEMultipart  # For handling email attachments
from IPython.display import Markdown, display  # For displaying tables in Jupyter
from dotenv import load_dotenv  # For loading environment variables
import urllib3  # For managing HTTP connections
from jinja2 import Environment, FileSystemLoader
import datetime
import csv
import pprint
import subprocess

# Suppress SSL warnings for sites with invalid certificates (if necessary)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables from .env file
load_dotenv()  # For email credentials (SENDER_EMAIL, SENDER_PASSWORD)


# %%

PREDOC_URL = "https://predoc.org/opportunities"
NBER_URL = "https://www.nber.org/career-resources/research-assistant-positions-not-nber"
EJM_URL = "https://econjobmarket.org/market"
XML_FILE = "jobs.xml"
csv_file_path = "subscribers.csv"
# Define your GitHub repository link
GITHUB_REPO_URL = "https://github.com/RickyJ99/RA-rss"
GITHUB_ISSUE_URL = f"{GITHUB_REPO_URL}/issues"

# %% [markdown]
# ## Downloading the html
# The following functions are downloading the HTML content from the sources and it save it in the foulder sources.
# For PREDOC there is a issue with certificate so it is easy to use curl (bash MacOS)

# %% [markdown]
# ## Downloading the html
# The following functions are downloading the HTML content from the sources and it save it in the foulder sources.
# For PREDOC there is a issue with certificate so it is easy to use curl (bash MacOS)

# %%
# Ensure the "sources" directory exists
os.makedirs("sources", exist_ok=True)

# Download the HTML file using curl
subprocess.run(
    ["curl", "-L", "https://predoc.org/opportunities", "-o", "sources/predoc.html"],
    check=True,
)


# %%
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


def read_preferences(csv_file):
    """
    Reads a CSV file containing names, emails, preferences, and universities.

    Expected CSV Format:
    name, email, preferences, university
    -------------------------------------
    John Doe, johndoe@example.com, Microeconomics/Labor Economics/Development, Harvard University
    Jane Smith, janesmith@example.com, Macroeconomics/Finance, MIT
    Harry, harry@example.com, ,

    :param csv_file: Path to the CSV file.
    :return: List of dictionaries with extracted data.
    """
    preferences_list = []

    try:
        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Extract values, ensuring no leading/trailing spaces
                name = row.get("name", "").strip()
                email = row.get("email", "").strip()
                university = (
                    row.get("university", "").strip() if "university" in row else "N/A"
                )

                # Handle preferences correctly, splitting by "/" and cleaning up empty values
                raw_preferences = row.get("preferences", "").strip()
                preferences = (
                    [p.strip() for p in raw_preferences.split("/") if p.strip()]
                    if raw_preferences
                    else ["N/A"]
                )

                if name and email:
                    preferences_list.append(
                        {
                            "name": name,
                            "email": email,
                            "preferences": preferences if preferences else "N/A",
                            "university": university if university else "N/A",
                        }
                    )

        return preferences_list

    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []


# %% [markdown]
# ## Extract Main Field Helper Function 🔑
#
# The `extract_main_field` function analyzes a given text to determine which research fields are mentioned. It searches for multiple keywords in a **case-insensitive** manner. If one or more keywords are found, it returns them as a comma‑separated string. If "N/A" are found, it returns `"N/A"`.
#
# ### Keywords Included:
# - **Economics**
# - **Macroeconomics**
# - **Microeconomics**
# - **Labour**
# - **Industrial Organization**
# - **Enterpreneurship**
# - **Healthcare**
# - **Discrimination**
# - **Finance**
# - **Public Policy**
#
# You can extend this list with additional fields in economics as needed.


# %%
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


# %% [markdown]
# **Function: `extract_program_type(text)`**
#
# - **Purpose:**
#   This function takes a string as input (which might be a job title or description) and determines the program type based on certain keywords.
#
# - **How It Works:**
#   1. **Convert to Lowercase:**
#      The input text is converted to lowercase to ensure case-insensitive matching.
#   2. **Keyword Checks:**
#      - If the text contains any variation of "predoctoral" (e.g., "predoctoral", "pre doc", "pre-doc", "predoc"), it returns **"PreDoctoral Program"**.
#      - If the text contains any variation of "postdoc" (e.g., "postdoc", "post doc", "post-doc", "postdoctoral", "post doctoral"), it returns **"Post Doc"**.
#      - If the text contains "phd" or "ph.d", it returns **"PhD"**.
#      - If the text mentions "research assistant" or even "ra" (for example, in abbreviated or extensive form), it returns **"Research Assistant"**.
#   3. **Default Category:**
#      If "N/A" of the keywords are found, the function defaults to returning **"Research Assistant"**.
#
#
#
#


# %%
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


# %% [markdown]
#
#
# ## Web Scraping Section 🚀
#
# In this section, we set up our web scraping functionality. Our goal is to **extract job details** from pre-doctoral opportunities pages (in this example, from [predoc.org](https://predoc.org/opportunities)). We assume that the HTML content has already been downloaded and saved locally in the `sources` folder.
#
# ### Predoc
# What This Section Does:
# - **Reads the Local HTML File 📂:**
#   We read the downloaded HTML file (`sources/predoc.html`). If the file isn't found, the code prompts you to download it first.
#
# - **Parses the HTML Content 🥣:**
#   Using BeautifulSoup, the code parses the HTML to locate the container that holds the opportunity details.
#
# - **Extracts Key Information 🔍:**
#   For each job posting, the function extracts:
#   - **Program Title** and **Link** from the `<h2>` element.
#   - Additional details (like **sponsor**, **institution**, **fields of research**, and **deadline**) from the "copy" `<div>`.
#
# - **Determines the Main Field 🔑:**
#   It combines several text fields and passes them to an auxiliary function (`extract_main_field()`) that determines the primary focus (e.g., Economics, Microeconomics, Finance, etc.).
#
# - **Returns the Data as a List 📤:**
#   Each job is stored as a dictionary, and the function returns a list of these dictionaries.
#
# > **Note:**
# > Make sure to download the HTML file before running the scraper (therefore run the previous chunks).
#


# %%
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

# %% [markdown]
# # Web Scraping Section for NBER (Local HTML) 🔎
#
# In this section, we extract job details from the locally saved NBER page HTML file. The function follows these steps:
#
# - **📂 Read the Local HTML File:**
#   The function attempts to read `sources/nber.html`. If the file isn't found, it prints an error message and returns an empty list.
#
# - **🥣 Parse HTML with BeautifulSoup:**
#   The HTML content is parsed so we can navigate and extract the data.
#
# - **🔍 Locate the Container:**
#   It finds the `<div>` with class `page-header__intro-inner` that holds the job details.
#
# - **✂️ Skip Header Paragraphs:**
#   The first three `<p>` elements are skipped as they contain header information.
#
# - **📋 Extract Job Details:**
#   For each job posting, the function extracts:
#   - Program title
#   - Sponsor
#   - Institution
#   - Fields of research
#   - Job link
#   If any of these details are missing, it defaults to `"N/A"`.
#
# - **🔑 Determine Main Field:**
#   It combines relevant text and uses the helper function `extract_main_field()` (which should be defined elsewhere) to determine the primary research area.
#
# - **✅ Return the Jobs List:**
#   Finally, all extracted job entries are stored in a list and returned.
#


# %%
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

# %% [markdown]
# ### Web Scraping Section for EJM (Econ Job Market) 🔎
#
# This function is designed to scrape job postings from the Econ Job Market (EJM) page. It performs the following tasks:
#
# - **🌐 Fetching the Page:**
#   It sends an HTTP GET request to the EJM URL using the `requests` library.
#
# - **🥣 Parsing HTML:**
#   The response content is parsed with BeautifulSoup to create a DOM structure for extraction.
#
# - **🔍 Locating Job Panels:**
#   It finds all `<div>` elements with the classes `"panel panel-info"`, each representing a job posting.
#
# - **🏷️ Extracting Job Details:**
#   For each panel, it extracts:
#   - **Job Title & Link:** Located within an `<a>` tag with an ID starting with "title-".
#   - **University & Program Type:** Extracted from `<div>` elements with class `"col-md-4"` and `"col-md-2"`, respectively.
#   - **Publication Date & Deadline:** Extracted from `<div>` elements with class `"col-md-2"`.
#   - **Default Values:** Fields such as **sponsor**, **institution**, and **fields** are set to `"N/A"` since they're not provided.
#
# - **🔑 Determining the Main Field:**
#   It combines the program title and university information to deduce the primary research field using the helper function `extract_main_field()`.
#
# - **✅ Building the Result List:**
#   Each job is stored as a dictionary, and all such dictionaries are appended to a list which is then returned.
#
#


# %%
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

# %% [markdown]
# ## CSV & Email Handling Section 📊✉️
#
# This section contains helper functions to manage your job database and send email notifications when new opportunities are detected.
#
# ### 1. Reading Existing Jobs from a CSV File 📂
#
# The `read_existing_jobs()` function reads a CSV file that contains saved job listings and returns a **set** of job links that are already recorded.
# - It checks if the file exists.
# - It uses Python's `csv.DictReader` to iterate over rows and collects the "link" field for each job.
#
# ### 2. Appending New Jobs to the CSV File 💾
#
# The `append_jobs_to_csv()` function takes a list of job dictionaries and appends them to the specified CSV file.
# - If the CSV file doesn't exist, it creates the file and writes the header.
# - It then appends each job as a new row.
#
# ### 3. Sending Email Notifications ✉️
#
# - **Purpose:**
#   This function sends an email notification whenever new job records are found.
#   - **Single Record:** The subject is set to the university name from that record.
#   - **Multiple Records:** The subject lists the unique university names (e.g., "University A, University B").
#
# - **Email Body:**
#   The email body is constructed as an HTML document with a styled table that lists:
#   - **Source** (e.g., "predoc", "nber", "ejm")
#   - **Program Title**
#   - **Clickable Link** (each link is rendered as a clickable hyperlink)
#   - **Sponsor**
#   - **Institution**
#   - **Fields**
#   - **Main Field**
#   - **Deadline**
#   - **University**
#   - **Program Type**
#   - **Publication Date**
#
# - **How It Works:**
#   1. **Subject Creation:**
#      The function extracts university names from each job record. If there's only one record, it uses that university name; if multiple, it joins all unique names.
#
#   2. **HTML Table Construction:**
#      An HTML table is built with one row per job record, ensuring that links are rendered as clickable hyperlinks.
#
#   3. **Email Assembly:**
#      The email is composed as a multipart message with both plain text and HTML parts.
#
#   4. **Sending the Email:**
#      Using Python's `smtplib`, the function logs in to the SMTP server (defaulting to Gmail) and sends the email.
#
#


# %%
def replace_none_or_empty_in_list_of_dicts(jobs):
    """
    Ensures all job dictionaries have consistent formatting:
    - Replace None or empty values with "N/A"
    - Strip extra whitespace
    - Convert to lowercase for consistency
    """
    cleaned_jobs = []
    for job in jobs:
        cleaned_job = {
            str(k).strip().lower(): str(v).strip() if v and v.strip() else "N/A"
            for k, v in job.items()
        }
        cleaned_jobs.append(cleaned_job)
    return cleaned_jobs


def read_existing_jobs(xml_file):
    """
    Reads existing job entries from XML and returns a dictionary of frozenset job signatures,
    categorized by 'source' (e.g., Predoc, NBER, EJM).

    If the XML file does not exist, returns an empty dictionary.
    """
    existing_signatures = {}

    if os.path.exists(xml_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for entry in root.findall("entry"):
            job_data = {
                child.tag.strip(): child.text.strip() if child.text else "N/A"
                for child in entry
            }
            job_signature = frozenset(
                sorted(job_data.items())
            )  # Sort keys to ensure consistency

            source = job_data.get("source", "Unknown")  # Extract source

            if source not in existing_signatures:
                existing_signatures[source] = (
                    set()
                )  # Create a set for this source if it doesn’t exist

            existing_signatures[source].add(
                job_signature
            )  # Store the signature under the correct source

    print("\n🔍 Debug: Existing Job Signatures by Source from XML")
    for src, sigs in existing_signatures.items():
        print(f"📁 {src}: {len(sigs)} jobs stored")

    return existing_signatures


def append_jobs_to_xml(xml_file, jobs):
    """
    Saves a list of job dictionaries into an XML file.

    - If the file does not exist, it creates a new XML structure.
    - If the file exists, it appends only new job entries while avoiding duplicates.
    """
    # Load existing XML or create a new root if the file doesn't exist
    if os.path.exists(xml_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()
    else:
        root = ET.Element("jobs")  # Create root element

    # Read existing jobs to avoid duplicates
    existing_signatures = read_existing_jobs(xml_file)

    new_entries_count = 0  # Track new records added

    for job in jobs:
        # Convert job dict into a frozenset signature
        job_str_dict = {
            str(k).strip(): str(v).strip() for k, v in job.items() if v != "N/A"
        }
        job_signature = frozenset(sorted(job_str_dict.items()))

        if job_signature not in existing_signatures:
            # This is a new job! Add it to XML.
            entry = ET.SubElement(root, "entry")

            for key, value in job.items():
                field = ET.SubElement(entry, key)
                field.text = value if value.strip() else "N/A"  # Ensure no empty values

            new_entries_count += 1

    # Only save if new entries were added
    if new_entries_count > 0:
        tree = ET.ElementTree(root)
        tree.write(xml_file, encoding="utf-8", xml_declaration=True)
        print(f"✅ {new_entries_count} new job(s) added to {xml_file}")
    else:
        print("🔹 No new jobs found; XML file remains unchanged.")


def send_email_new_jobs(
    new_jobs,
    sender_email,
    sender_password,
    subscribers,
    smtp_server="smtp.gmail.com",
    smtp_port=587,
):
    """
    Sends personalized job update emails to each subscriber based on their preferences.

    - Uses Jinja2 for templating.
    - Loads email HTML template from `templates/email.html`.
    - Includes "Apply" buttons instead of raw links.
    - Displays the latest update timestamp.
    - Provides links to contribute or report issues on GitHub.

    Parameters:
        new_jobs (list): List of dictionaries containing new job data.
        sender_email (str): Email address used to send emails.
        sender_password (str): App password for authentication.
        subscribers (list of dicts): List of subscriber dictionaries with 'name', 'email', and 'preferences'.
        smtp_server (str): SMTP server address (default: "smtp.gmail.com").
        smtp_port (int): SMTP server port (default: 587).
    """

    # Get the current date & time
    update_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Load the email template using Jinja2
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("email.html")

    for subscriber in subscribers:
        recipient_name = subscriber.get("name", "Subscriber")
        recipient_email = subscriber.get("email")
        preferences = subscriber.get("preferences", "")

        if not recipient_email:
            continue  # Skip if email is missing

        filtered_jobs = new_jobs  # No filter applied if preferences are empty

        # Skip sending email if no relevant jobs for this user
        if not filtered_jobs:
            continue

        # Count filtered jobs for the subject line
        num_jobs = len(filtered_jobs)
        subject = f"New Job Opportunities Found ({num_jobs})"

        # Render the email with personalized details
        html_body = template.render(
            recipient_name=recipient_name,
            new_jobs=filtered_jobs,
            update_time=update_time,
            github_repo_url=GITHUB_REPO_URL,
            github_issue_url=GITHUB_ISSUE_URL,
        )

        # Create a multipart email message (plain text and HTML)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email

        # Plain text fallback
        text_body = f"Hello {recipient_name},\n\nWe found {num_jobs} new research assistant or pre-doctoral positions that match your interests.\nPlease view this email in an HTML-compatible client to see the job listings with 'Apply' buttons."

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
            print(f"✅ Email sent successfully to {recipient_email}!")
        except Exception as e:
            print(f"❌ Failed to send email to {recipient_email}: {e}")


def find_new_jobs():
    """
    Scrapes jobs from each source, checks for duplicates using XML storage,
    and returns a list of newly detected jobs.
    """
    # Scrape jobs from each source.
    predoc_jobs = scrape_predoc()
    nber_jobs = scrape_nber()
    ejm_jobs = scrape_ejm()

    # Combine all job records into a single list.
    all_jobs = predoc_jobs + nber_jobs + ejm_jobs
    all_jobs = replace_none_or_empty_in_list_of_dicts(all_jobs)

    if not all_jobs:
        print("No jobs were scraped.")
        return []

    # Read existing job signatures from XML.
    existing_signatures = read_existing_jobs(XML_FILE)

    print("\n🔍 Debug: Checking New Jobs Against Filtered Existing Records")

    new_jobs = []
    for job in all_jobs:
        job_str_dict = {
            str(k).strip().lower(): str(v).strip() if v and v.strip() else "N/A"
            for k, v in job.items()
        }
        job_signature = frozenset(sorted(job_str_dict.items()))

        # Use `source` to filter existing records before comparison
        job_source = job.get("source", "Unknown")

        if (
            job_source in existing_signatures
            and job_signature in existing_signatures[job_source]
        ):
            print(f"✅ Job Already Exists in XML ({job_source})")
        else:
            print(f"❌ New Job Detected! Adding to list. ({job_source})")
            new_jobs.append(job)

    print(f"\nFound {len(new_jobs)} new job(s).")
    return new_jobs  # Return list of new jobs


def debug_email_with_existing_jobs(existing_jobs):
    """
    Debug function to render the email using existing jobs.
    """
    from jinja2 import Environment, FileSystemLoader
    import datetime

    # Flatten jobs from all sources into a single list
    all_jobs = []
    for source, jobs in existing_jobs.items():
        for job in jobs:
            # Convert frozenset back to dict if necessary
            if isinstance(job, frozenset):
                job = dict(job)
            all_jobs.append(job)

    if not all_jobs:
        print("⚠️ No existing jobs found in the XML file.")
        return

    # Take only the first 5 jobs for debugging
    sample_jobs = all_jobs[:5]

    print("\n🔍 DEBUG: First 5 Jobs for Email Rendering")
    for job in sample_jobs:
        print(job)

    # Load the email template using Jinja2
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("email.html")

    # Get the current timestamp
    update_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Render the email with the sample job data
    email_content = template.render(
        new_jobs=sample_jobs,
        update_time=update_time,
        github_repo_url="https://github.com/your_repo",
        github_issue_url="https://github.com/your_repo/issues",
    )

    print("\n📝 DEBUG: Rendered Email Content (Raw HTML):\n", email_content)

    # Save the output to a file for testing
    with open("debug_email_output.html", "w", encoding="utf-8") as f:
        f.write(email_content)

    print(
        "\n✅ Email template successfully rendered and saved as 'debug_email_output.html'."
    )


# Load existing jobs from XML (assuming you have a function for this)
# existing_jobs = read_existing_jobs(XML_FILE)

# Call the debug function
# debug_email_with_existing_jobs(existing_jobs)


# %% [markdown]
# ## Main Function: Scrape, Update, and Notify 🚀📊✉️
#
# This **main()** function orchestrates the complete workflow of the project. It:
#
# - **Scrapes Job Data:**
#   Calls the scraping functions for all three sources (Predoc, NBER, EJM) to collect job postings.
#
# - **Filters New Jobs:**
#   Reads an existing CSV file (acting as a simple database) to get a set of already recorded job links. Then, it filters out jobs that are already present.
#
# - **Sends Notifications:**
#   For each new job found, the function sends an email notification with the job details.
#
# - **Updates the CSV Database:**
#   Finally, it appends the new job entries to the CSV file for future reference.
#
# > **Note:**
# > Ensure that your SMTP credentials (i.e. `SENDER_EMAIL` and `SENDER_PASSWORD`) are set up and that the scraping functions (`scrape_predoc()`, `scrape_nber()`, and `scrape_ejm()`) along with CSV and email helper functions are defined before running `main()`.


# %%
def main():
    """
    Main execution function. Calls find_new_jobs, saves new jobs to XML,
    and optionally sends email notifications.
    """
    new_jobs = find_new_jobs()  # Call the new function

    if new_jobs:
        # Save new jobs to XML instead of CSV. 💾
        append_jobs_to_xml(XML_FILE, new_jobs)

        # Retrieve SMTP credentials from environment variables. 🔒
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")
        subscribers = read_preferences(csv_file_path)

        # Convert new jobs to a DataFrame for better visualization.
        df_new = pd.DataFrame(new_jobs).head(10)
        md_table = df_new.to_markdown(index=False)

        # Uncomment to send email notifications
        send_email_new_jobs(new_jobs, sender_email, sender_password, subscribers)

    else:
        print("No new jobs found.")
        if os.path.exists(XML_FILE):
            df_new = pd.read_xml(XML_FILE).head(10)
            md_table = df_new.to_markdown(index=False)
        else:
            md_table = "No XML file found."

    # Display the table in the notebook (either new jobs or existing XML).
    display(Markdown(md_table))


# %%
if __name__ == "__main__":
    main()
