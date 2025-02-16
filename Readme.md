# 📌 Research Assistant Job Scraper

## 📝 Project Overview
This project is designed to **scrape job listings** for research assistant and pre-doctoral positions from multiple sources, process the data, and display it in a **web interface** for easy filtering and viewing. It also allows **automatic updates** and **email notifications** when new positions are found.

## 📂 Folder Structure
```
├── app.py                   # Flask web app for viewing job listings
├── environment.yml          # Conda environment configuration
├── jobs.xml                 # Stores the latest scraped job listings
├── main.ipynb               # Jupyter notebook for manual testing
├── main.py                  # Main script to scrape jobs and update XML
├── previous_jobs.xml        # Backup of the previous job listings
├── sources                  # Directory for downloaded HTML pages
│   ├── ejm.html             # Cached EJM job listings
│   ├── nber.html            # Cached NBER job listings
│   └── predoc.html          # Cached Predoc job listings
├── static                   # Static files for the web app
│   └── style.css            # CSS for dark mode styling
└── templates                # HTML templates for Flask
    └── index.html           # Main page displaying job listings
```

## 🚀 How to Set Up the Project
### 1️⃣ Install Dependencies
You can create the necessary environment using Conda:
```sh
conda env create -f environment.yml
conda activate ra
```
Alternatively, if you are using `pip`:
```sh
pip install -r requirements.txt
```

### 2️⃣ Set Up Environment Variables
To configure email notifications, create a `.env` file in the root folder and add:
```
SENDER_EMAIL=your_email@example.com
SENDER_PASSWORD=your_app_password
```
> ⚠️ **Important**: For Gmail, you need to generate an **App Password** instead of using your actual password.

## 🌍 Web Scraping (Downloading HTML Pages)
### Automated Download (MacOS & Linux)
In **MacOS** and **Linux**, the script includes these two commands to **download the HTML of the Predoc site** and save it in `sources/`:
```sh
!mkdir -p sources
!curl -L "https://predoc.org/opportunities" -o "sources/predoc.html"
```
> **Windows Alternative**: These commands won't work on **Windows**. You should manually open the **Predoc** website, save the **HTML file**, and place it in the `sources/` folder.

## ⏳ Automating Execution (MacOS/Linux)
To **run `main.py` automatically every day at 16:00**, you can create a **Cron Job**:
```sh
crontab -e
```
Then add the following line:
```sh
0 16 * * * /bin/bash -c 'source ~/miniconda3/etc/profile.d/conda.sh && conda activate ra && python ~/path/to/main.py >> ~/cron_log.txt 2>&1'
```
To **monitor the logs**, run:
```sh
tail -f ~/cron_log.txt
```
> If you are using **Windows**, you should create a **Task Scheduler** job instead.

## 🌐 Running the Web App
Once you have scraped job data into `jobs.xml`, you can launch the **Flask web app**:
```sh
python app.py
```
Then open **http://127.0.0.1:5000** in your browser.

## 🤝 Contributing
This is an **open-source project**, and contributions are **welcome!** 🚀 If you would like to **improve the web scraping**, **optimize performance**, or **enhance the web interface**, feel free to submit **pull requests** or report issues.

