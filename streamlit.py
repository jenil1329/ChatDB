import streamlit as st
import pymysql
from pymongo import MongoClient
import logging
import openai
from openai import OpenAI
import re
import shlex

# ——— Set up logging ———
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

# Set OpenAI API Key (replace with your actual key)
openai.api_key = ''

@st.cache_resource
# MongoDB Connection
def connect_mongo():
    client = MongoClient("mongodb://localhost:27017/")
    db = client['market_data']
    return db

# ——— MySQL Connection ——— (unchanged)
def connect_mysql():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        db='market_data',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
def is_text_output_query(sql_query):
    text_output_patterns = [
        r'^show\s+tables', 
        r'^show\s+databases', 
        r'^show\s+columns\s+from', 
        r'^describe\s+',
        r'^desc\s+'
    ]
    query = sql_query.strip().lower()
    return any(re.match(pattern, query) for pattern in text_output_patterns)

# ——— MySQL Handler ——— (unchanged)
def handle_mysql_query(query):
    logger.debug(f"Attempting MySQL query: {query}")
    conn = None
    try:
        conn = connect_mysql()
        cursor = conn.cursor()
        cursor.execute(query)

        if is_text_output_query(query):
            rows = cursor.fetchall()
            if rows:
                formatted = '\n'.join([' | '.join(str(v) for v in row.values()) for row in rows])
            else:
                formatted = "No results."
            return formatted

        if query.strip().lower().startswith('select'):
            rows = cursor.fetchall()
            logger.debug(f"Fetched {len(rows)} rows")
            result = rows
        else:
            conn.commit()
            affected = cursor.rowcount
            logger.debug(f"Query affected {affected} rows")
            result = [{"affected_rows": affected}]
    except Exception as e:
        logger.error("Error executing MySQL query", exc_info=True)
        result = f"Error executing MySQL query: {e}"
    finally:
        if conn:
            conn.close()
    return result
# General MongoDB Query Handler (Direct Execution)
def handle_mongo_query(query_dict):
    try:
        db = connect_mongo()
        operation = query_dict.get("operation")

        # List all collections (no collection name needed)
        if operation == "listCollections":
            return db.list_collection_names()

        collection_name = query_dict.get("collection")
        collection = db[collection_name]

        if operation == "find":
            arguments = query_dict["arguments"]

            if isinstance(arguments, dict):
                filter_query = arguments.get("filter", {})
                projection = arguments.get("projection", None)
                sort = arguments.get("sort")
                limit = arguments.get("limit")

                result = collection.find(filter_query, projection or {})

                if sort:
                    result = result.sort(list(sort.items()))
                if limit:
                    result = result.limit(limit)

            elif isinstance(arguments, list) and len(arguments) == 2:
                filter_query, projection = arguments
                result = collection.find(filter_query, projection)
            else:
                result = collection.find(arguments)

            return list(result)

        elif operation == "aggregate":
            pipeline = query_dict["arguments"]

            # 💥 NEW: Check if lookup exists and add unwind dynamically
            new_pipeline = []
            for stage in pipeline:
                new_pipeline.append(stage)
                if "$lookup" in stage:
                    lookup_stage = stage["$lookup"]
                    as_field = lookup_stage.get("as")
                    if as_field:
                        # Add $unwind stage after the $lookup
                        new_pipeline.append({"$unwind": f"${as_field}"})

            return list(collection.aggregate(new_pipeline))

        elif operation == "findOne":
            return collection.find_one()

        elif operation == "insertOne":
            document = query_dict["arguments"]
            result = collection.insert_one(document)
            return {"inserted_id": str(result.inserted_id)}

        elif operation == "insertMany":
            documents = query_dict["arguments"]
            result = collection.insert_many(documents)
            return {"inserted_ids": [str(_id) for _id in result.inserted_ids]}

        elif operation == "updateOne":
            filter_query, update_fields = query_dict["arguments"]
            result = collection.update_one(filter_query, {"$set": update_fields})
            return {
                "matched_count": result.matched_count,
                "modified_count": result.modified_count
            }

        elif operation == "deleteOne":
            filter_query = query_dict["arguments"]
            result = collection.delete_one(filter_query)
            return {"deleted_count": result.deleted_count}

        else:
            return {"error": f"Unsupported operation: {operation}"}

    except Exception as e:
        return {"error": str(e)}

# Function to use OpenAI GPT to convert natural language into database query
def generate_database_query(natural_language_query: str, db_type: str):
    client = OpenAI(api_key=openai.api_key)
    if db_type == "MySQL":
        # SQL schema context for MySQL remains unchanged
        schema_context = (
            "You are a helpful assistant that generates valid SQL queries for MySQL. "
            "The schema is as follows:\n\n"
            "1) Table `market_symbol`:\n"
            "   • `symbol` VARCHAR(10) PRIMARY KEY\n"
            "   • `company_name` VARCHAR(255)\n"
            "   • `sector` VARCHAR(255)\n"
            "   • `industry` VARCHAR(255)\n\n"
            "2) Table `market_data`:\n"
            "   • `symbol` VARCHAR(10)\n"
            "   • `date` DATE\n"
            "   • `open_price`, `high_price`, `low_price`, `close_price` DECIMAL(10,2)\n"
            "   • `volume` BIGINT\n"
            "   • PRIMARY KEY(symbol, date)\n"
            "   • FOREIGN KEY(symbol) REFERENCES market_symbol(symbol)\n\n"
            "3) Table `technical_indicators`:\n"
            "   • `symbol` VARCHAR(10)\n"
            "   • `date` DATE\n"
            "   • `indicator_type` VARCHAR(20)  -- e.g. 'SMA','EMA','WMA','DEMA'\n"
            "   • `indicator_value` DECIMAL(12,6)\n"
            "   • PRIMARY KEY(symbol, date, indicator_type)\n"
            "   • FOREIGN KEY(symbol) REFERENCES market_symbol(symbol)\n\n"
            "Guidelines:\n"
            "- When you need price history, query `market_data`.\n"
            "- For company metadata, join to `market_symbol`:\n"
            "    e.g. `JOIN market_symbol m ON m.symbol = d.symbol`\n"
            "- For indicator queries, join to `technical_indicators` on symbol+date.\n"
            "- Always filter by the ticker (e.g. WHERE symbol = 'AAPL'), not by numeric ID.\n"
            "- Use `CURDATE()` and `INTERVAL` for date math.\n"
            "- Return ONLY the SQL query (no explanation or commentary)."
        )
    elif db_type == "MongoDB":
        schema_context = (
            """
              You are a helpful assistant that generates structured MongoDB query objects based on natural language input.
              The database is named `market_data`. The collections and their fields are:
              1. `market_sentiment`:
                     - _id
                     - news_url
                     - sentiment
                     - sentiment_score
                     - symbol
                     - timestamp

              2. `earnings_transcripts`:
                     - _id
                     - quarter
                     - symbol
                     - call_date
                     - timestamp
                     - speaker
                     - title
                     - content
                     - sentiment

              3. `market_news`:
                     - _id
                     - url
                     - date
                     - headline
                     - summary
                     - symbol

              You must return a valid JSON object with this format:
              {
                "operation": "<find | aggregate | insertOne | insertMany | updateOne | deleteOne | findOne | listCollections>",
                "collection": "<collection_name (omit if listCollections)>",
                "arguments": <query arguments or pipeline>
              }

              Rules:
              - Use MongoDB syntax only.
              - Use `"findOne"` for a sample document.
              - Use `"listCollections"` without a `collection` key.
              - Do not include explanations, comments, or triple backticks.
              - Always return a valid JSON object, parseable directly by Python.

              Example NL input:  
              **"Get average sentiment score for AAPL from market_sentiment."**

              Example output:  
              {
                "collection": "market_sentiment",
                "operation": "aggregate",
                "arguments": [
                  { "$match": { "symbol": "AAPL" } },
                  { "$group": { "_id": null, "avg_sentiment": { "$avg": "$sentiment_score" } } }
                ]
              }
              Example output for bundled sort and limit:
              {
                "collection": "earnings_transcripts",
                "operation": "find",
                "arguments": {
                "filter": { "symbol": "AAPL" },
                "projection": null,
                "sort": { "call_date": -1 },
                "limit": 5
              }
       }
       When answering questions that ask for fields from multiple collections (e.g., sentiment and headlines), use $lookup to join collections using news_url ↔ url, and project only the requested fields.
            Note - Facebook has market symbol META
            Google has market sybmbol GOOG or GOOGL
            Amazon has market symbol AMZN
            Netflix has market symbol NFLX
            Microsoft has market symbol MSFT
            Apple has market symbol AAPL
            Tesla has market symbol TSLA
            """
        )

    messages = [
        {"role": "system", "content": schema_context},
        {"role": "user", "content": f"Convert the following request into a valid query: {natural_language_query}"}
    ]
   
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )
   
    result = completion.choices[0].message.content.strip()
   
    result = re.sub(r"^```(json|mongodb)?\n?", "", result)
    result = result.strip("` \n")

    print(f"Cleaned MongoDB Query: {result}")
    return result

# Streamlit app with LLM integration and radio buttons
def main():
    st.title("Database Query Interface with LLM")
    st.write("Select a database service and enter your natural language query below:")
   
    db_choice = st.radio("Select Database Service:", ["MySQL", "MongoDB"])
    query_input = st.text_area("Enter your query:")
   
    if st.button("Submit"):
        if not query_input:
            st.write("Please enter a query.")
            return

        generated_query = generate_database_query(query_input, db_choice)
        #st.write(f"Generated Query: {generated_query}")
       
        if db_choice == "MySQL":
            result = handle_mysql_query(generated_query)
            st.write("MySQL Query Result:")
            st.write(result)
        elif db_choice == "MongoDB":
              try:
                     structured_query = json.loads(generated_query)
                     result = handle_mongo_query(structured_query)
              except Exception as e:
                     result = {"error": f"Failed to parse or run query: {e}"}
              st.write("MongoDB Query Result:")
              st.write(result)
        else:
            st.write("Invalid database selection.")

if __name__ == "__main__":
    main()
