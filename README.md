# 🧠 ChatDB  – Natural Language Financial Data Query Engine

ChatDB  is an AI-powered system that enables users to query financial market and sentiment data using natural language. It translates plain English queries into SQL and MongoDB queries, retrieves data from multiple sources, and presents results through interactive visualizations.

## 🚀 Overview
This project demonstrates how Large Language Models (LLMs) can be integrated with structured and unstructured data systems to build intuitive data access tools.
Users can:
* Ask financial questions in plain English
* Retrieve data from multiple databases
* Visualize results instantly

## ✨ Key Features
 💬 Natural language query interface powered by GPT-4
 🗃️ Dual database support:

* MySQL (structured financial/market data)
*   MongoDB (news and sentiment data)
* 📊 Interactive visualizations using Streamlit
* 🔄 Real-time data integration via Alpha Vantage API
* ⚙️ Automatic query generation and execution


## 🏗️ System Architecture

* **Frontend:** Streamlit
* **LLM Layer:** OpenAI GPT-4
* **Databases:** MySQL + MongoDB
* **Data Source:** Alpha Vantage API
* **Backend Logic:** Python


## 🧰 Prerequisites

Make sure the following are installed:
* Python 3.8+
* Git
* MySQL Server (localhost:3306)
* MongoDB Server (localhost:27017)
## 🔑 Environment Setup
Create a `.env` file in the root directory:


OPENAI_API_KEY=your_api_key_here

## ⚙️ Installation & Setup

### 1. Clone the repository

git clone https://github.com/yourusername/chatdb21.git
cd chatdb21

### 2. Create virtual environment (recommended)
**Windows**
python -m venv venv
venv\Scripts\activate

**macOS/Linux**

python3 -m venv venv
source venv/bin/activate

### 3. Install dependencies

pip install -r requirements.txt

### 4. Database Setup
#### MySQL

* Ensure MySQL server is running
* Create database:


CREATE DATABASE market_data;

* Update credentials in config file if required:

```python
mysql_config = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password',
    'database': 'market_data'
}
```
#### MongoDB

* Ensure MongoDB is running on port `27017`
* Collections will be created automatically

### 5. Run the application
```
streamlit run streamlit_app.py
```
Open in browser:
```
http://localhost:8501
```
## 📁 Project Structure

```
chatdb21/
├── mongo_data/          # MongoDB collections
├── mysql_data/          # MySQL data files
├── requirements.txt     # Dependencies
├── streamlit_app.py     # Main application
└── README.md            # Documentation
```

## 🔍 Example Use Cases

* “Show me top performing stocks this month”
* “Compare Tesla vs Apple stock trends”
* “What is the sentiment around Nvidia in recent news?”


## ⚠️ Limitations

* LLM-generated queries may occasionally produce incorrect SQL
* Performance depends on API rate limits and database size
* Requires local database setup

## 📌 Future Improvements

* Add query validation and correction layer
* Improve handling of ambiguous queries
* Deploy as a web application
* Add user authentication
* 
## 👨‍💻 Author

Jenil Jasani
Master’s in Data Science – Macquarie University


## ⭐ Why this project matters

This project demonstrates:

* LLM + database integration
* Real-world data querying systems
* Practical application of AI in financial analytics

