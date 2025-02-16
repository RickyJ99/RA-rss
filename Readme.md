# 📌 Research Assistant Job Scraper

## 📝 Project Overview
This project **scrapes job listings** for **research assistant (RA)** and **pre-doctoral positions** from multiple sources, **stores them in an XML file**, and **displays them in a web interface** with filtering and sorting options. It also sends **email notifications** when new positions are found.

### 🔹 Features:
- ✅ **Automatic job scraping** from multiple sources
- ✅ **Web-based job viewer** (built with Flask)
- ✅ **Daily automatic updates** via cron job (Mac/Linux) or Task Scheduler (Windows)
- ✅ **Email alerts** for new job listings
- ✅ **Public subscription via GitHub** 📩

---

## 📩 **Subscribe for Job Alerts**
To receive **email notifications** when **new job listings** are found, submit a **GitHub issue request**:

👉 **[Subscribe Here](https://github.com/RickyJ99/RA-rss/issues/1)**

> **🔒 Your email will NOT be publicly visible.**  
> We will securely add it to our mailing list. 🚀

---

## 📂 Folder Structure
```
📁 Project Folder
├── app.py                   # Flask web app for viewing job listings
├── environment.yml          # Conda environment configuration
├── jobs.xml                 # Stores the latest scraped job listings
├── main.ipynb               # Jupyter notebook for testing the scraper
├── main.py                  # Main script to scrape jobs and update XML
├── previous_jobs.xml        # Backup of the previous job listings
├── sources                  # Directory for downloaded HTML pages
│   ├── ejm.html             # Cached EJM job listings
│   ├── nber.html            # Cached NBER job listings
│   └── predoc.html          # Cached Predoc job listings
├── static                   # Static files for the web app
│   └── style.css            # CSS for dark mode styling
├── templates                # HTML templates for Flask
│   ├── index.html           # Main page displaying job listings
│   ├── email.html           # Template for job notification emails
└── .env                     # Environment variables (email credentials)
```

---

## 🚀 Installation & Setup

### **1️⃣ Install Dependencies**
#### **Using Conda**:
```sh
conda env create -f environment.yml
conda activate ra
```
#### **Using Pip**:
```sh
pip install -r requirements.txt
```

### **2️⃣ Set Up Environment Variables**
For email notifications, create a `.env` file in the project root and add:
```sh
SENDER_EMAIL=your_email@example.com
SENDER_PASSWORD=your_app_password
```
> 🔴 **Note:** If using Gmail, **generate an App Password** instead of your actual password.

---

## 🌍 Web Scraping (Downloading HTML Pages)

### **Automated Download (MacOS & Linux)**
The script **automatically downloads the Predoc HTML page** and saves it in the `sources/` directory using:
```sh
mkdir -p sources
curl -L "https://predoc.org/opportunities" -o "sources/predoc.html"
```
### **Manual Download (Windows)**
The above commands **won’t work on Windows**. Instead:
1. Open the **Predoc** website in your browser.
2. **Right-click → Save as...** (HTML file).
3. Save it in the **`sources/`** folder.

---

## ⏳ Automating Execution (Mac/Linux/Windows)

### **MacOS & Linux (Cron Job)**
To schedule **daily execution at 16:00**, open the cron editor:
```sh
crontab -e
```
Then add:
```sh
0 16 * * * /bin/bash -c 'source ~/miniconda3/etc/profile.d/conda.sh && conda activate ra && python ~/path/to/main.py >> ~/cron_log.txt 2>&1'
```
**Check logs with:**
```sh
tail -f ~/cron_log.txt
```

### **Windows (Task Scheduler)**
1. Open **Task Scheduler**.
2. Create a **new task**:
   - Set the **trigger**: **Daily at 16:00**.
   - Set the **action**: Run `python main.py` inside the **RA environment**.
   - Set **Start in:** `C:\path\to\your\project`
3. **Save & Enable the task.**

---

## 🌐 Running the Web App
After **scraping job data** into `jobs.xml`, you can **start the Flask web app**:
```sh
python app.py
```
Then, open **http://127.0.0.1:5000** in your browser.

---

## 📩 Email Notifications
When **new jobs are found**, an **HTML email** is sent with:
- **A table of new job listings** 📋
- **"Apply" buttons** instead of raw links 🎯
- **Updated timestamps** ⏳
- **Links to contribute or report issues on GitHub** 🔗

---

## 🤝 Contributing
This is an **open-source project**, and contributions are **welcome!** 🚀  
Ways to contribute:
- Improve **web scraping** logic 🕸
- Add **new job sources** 📄
- Enhance the **web interface** 🎨
- Improve **email formatting** 📩

👉 **[GitHub Repository](https://github.com/RickyJ99/RA-rss)**  
🐛 **[Report an Issue](https://github.com/RickyJ99/RA-rss/issues)**  