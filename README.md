# 🤖 Sakila Data AI Agent 📊

A powerful AI-powered chatbot that helps you analyze and query the Sakila database (a sample MySQL database representing a DVD rental store) using natural language. Built with OpenAI's GPT-4o-mini model, Python, and Streamlit.

## 🌟 Features

- 🗣️ **Natural Language Querying**: Ask questions in plain English and get SQL-powered answers
- 🤖 **AI-Powered Agent**: Uses OpenAI's GPT-4o-mini with function calling capabilities
- 🎨 **Interactive UI**: Beautiful, modern chat interface built with Streamlit
- 🔍 **Query Transparency**: See the generated SQL queries in expandable sections
- 📊 **Data Visualization**: Results displayed as interactive pandas DataFrames
- 🌐 **Flexible Database Support**: Works with both local MySQL and cloud PostgreSQL databases
- 🧠 **Schema-Aware**: Complete Sakila database schema embedded in the AI's context
- 🔧 **Tool Calling**: Advanced implementation using OpenAI's function calling API

## 🛠️ Prerequisites

- **Python 3.8+**
- **Database Options:**
  - Local: MySQL with Sakila database installed, OR
  - Cloud: PostgreSQL database (e.g., Neon, AWS RDS, Google Cloud SQL)
- **OpenAI API key** (get one at [platform.openai.com](https://platform.openai.com))
- **Required Python packages** (see Installation section)

## 📦 Installation & Setup

### 1. Fork & Clone the Repository

```bash
git clone https://github.com/yourusername/sakila-data-ai-agent.git
cd sakila-data-ai-agent
```

### 2. Install Required Packages

```bash
pip install -r requirements.txt
```

Or install core packages directly:
```bash
pip install openai streamlit pymysql sqlalchemy python-dotenv pandas psycopg
```

### 3. Set Up Your Database

#### Option A: Local MySQL Database

1. Install MySQL if you haven't already
2. Import the Sakila database using the SQL scripts provided:

```bash
# Run scripts in order:
mysql -u root -p < sakila-sql-scripts/sakila_schema_00_create_schema.sql
mysql -u root -p < sakila-sql-scripts/sakila_data_01_base_data.sql
mysql -u root -p < sakila-sql-scripts/sakila_data_02_location_data.sql
mysql -u root -p < sakila-sql-scripts/sakila_data_03_film_data.sql
mysql -u root -p < sakila-sql-scripts/sakila_data_04_staff_store_customer.sql
mysql -u root -p < sakila-sql-scripts/sakila_data_05a_rental_data_part1.sql
mysql -u root -p < sakila-sql-scripts/sakila_data_05b_rental_data_part2.sql
mysql -u root -p < sakila-sql-scripts/sakila_data_06a_payment_data_part1.sql
mysql -u root -p < sakila-sql-scripts/sakila_data_06b_payment_data_part2.sql
```

#### Option B: Cloud Database

See `Cloud_DB_Guide.ipynb` for detailed instructions on setting up a cloud PostgreSQL database with the Sakila data.

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=your_api_key_here

# Local MySQL Configuration (if using local database)
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_database_password
DB_NAME=sakila
DB_PORT=3306

# Cloud PostgreSQL Configuration (if using cloud database)
POSTGRES_HOST=your_cloud_host
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=sakila
POSTGRES_PORT=5432
```

## 🚀 Usage

### Start the Application

```bash
streamlit run app_solution.py
```

Or if you're building from scratch:
```bash
streamlit run app.py
```

### Using the Chatbot

1. Open your web browser to the provided local URL (typically `http://localhost:8501`)
2. Start asking questions about the Sakila database in natural language
3. View the AI's responses along with the generated SQL queries
4. Explore the data displayed in interactive tables

## 💡 Example Queries

Here are some questions you can ask:

**Basic Queries:**
- "How many movies are in the database?"
- "Show me all the actors"
- "What are all the film categories?"

**Complex Analytics:**
- "What are the top 10 most rented movies?"
- "Show me the top 5 customers by total rental count"
- "What's the average rental duration by film category?"
- "Which stores have the highest revenue?"

**Business Insights:**
- "Who are the most profitable customers?"
- "What are the most popular film categories by rental count?"
- "Show me monthly revenue trends"
- "Which actors appear in the most films?"

## 🗄️ Project Structure

```
sakila-data-ai-agent/
├── ai/                              # AI agent modules
│   ├── agent.py                     # Core agent implementation with tool calling
│   ├── tools.py                     # Database querying tools (local & cloud)
│   ├── prompts.py                   # System prompts with schema information
│   ├── sakila_schema.py             # Complete Sakila database schema
│   └── utils.py                     # Database connection utilities
├── sakila-sql-scripts/              # SQL scripts for database setup
│   ├── sakila_schema_00_create_schema.sql
│   ├── sakila_data_01_base_data.sql
│   ├── sakila_data_02_location_data.sql
│   ├── sakila_data_03_film_data.sql
│   ├── sakila_data_04_staff_store_customer.sql
│   ├── sakila_data_05a_rental_data_part1.sql
│   ├── sakila_data_05b_rental_data_part2.sql
│   ├── sakila_data_06a_payment_data_part1.sql
│   └── sakila_data_06b_payment_data_part2.sql
├── app.py                           # Starter template (build your own)
├── app_solution.py                  # Complete reference implementation
├── Developer_Guide.ipynb            # Comprehensive tutorial notebook
├── Cloud_DB_Guide.ipynb             # Cloud database setup guide
├── Structured_Output_Guide.ipynb   # Advanced: Using structured outputs
├── requirements.txt                 # Python package dependencies
├── .env                             # Environment variables (create this)
└── README.md                        # This file
```

## 🔧 Technical Details

### Architecture

The project implements a modern AI agent architecture using:

1. **OpenAI Function Calling**: The agent uses GPT-4o-mini with function calling to determine when to query the database
2. **Tool Implementation**: Custom Python functions that execute SQL queries and return formatted results
3. **Schema-Aware Prompting**: The complete Sakila database schema is embedded in the system prompt
4. **Stateful Conversation**: Streamlit session state maintains conversation history
5. **Dynamic SQL Generation**: The LLM generates SQL queries based on natural language input

### Key Technologies

- **OpenAI API (GPT-4o-mini)**: Natural language understanding and SQL generation
- **Streamlit**: Interactive web application framework
- **SQLAlchemy**: Database ORM and connection management
- **PyMySQL**: MySQL database adapter
- **Psycopg**: PostgreSQL database adapter
- **Pandas**: Data manipulation and display
- **Python-dotenv**: Environment variable management

### How It Works

1. User enters a natural language question in the chat interface
2. The message is sent to GPT-4o-mini along with the conversation history and database schema
3. The AI determines if a database query is needed and generates the appropriate SQL
4. The `get_data_df` tool executes the SQL query against the database
5. Results are formatted as a pandas DataFrame and displayed to the user
6. The AI provides a natural language response based on the data

## 📚 Learning Resources

This repository is designed as a comprehensive learning resource for building AI-powered data agents:

### 1. Developer Guide (`Developer_Guide.ipynb`)

A step-by-step Jupyter notebook that teaches you how to build the entire application:
- Setting up the OpenAI API and understanding API parameters
- Creating effective system prompts with database schemas
- Implementing function calling and tool use
- Building database connection utilities
- Developing the Streamlit chat interface
- Managing conversation state and history

### 2. Cloud Database Guide (`Cloud_DB_Guide.ipynb`)

Learn how to:
- Set up a cloud PostgreSQL database (Neon, AWS, GCP)
- Migrate the Sakila schema to PostgreSQL
- Import data into your cloud database
- Configure secure connections
- Modify the agent to work with cloud databases

### 3. Structured Output Guide (`Structured_Output_Guide.ipynb`)

Advanced topics including:
- Using OpenAI's structured output feature
- Implementing Pydantic models for response validation
- Type-safe AI responses
- Advanced prompt engineering techniques

### 4. Development Process

- Start with `app.py` - it's intentionally minimal for you to build up
- Follow the Developer Guide step by step
- Reference `app_solution.py` only after attempting to build it yourself
- Experiment with different prompts and queries
- Try extending the agent with additional tools and capabilities

### 5. Learning Goals

By working through this project, you'll learn:
- ✅ How to integrate OpenAI's API into Python applications
- ✅ Implementing AI function calling for tool use
- ✅ Building conversational AI agents
- ✅ Natural language to SQL query generation
- ✅ Database connectivity and query execution
- ✅ Creating interactive web applications with Streamlit
- ✅ Managing application state and conversation history
- ✅ Best practices for AI prompt engineering

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

### Using AI Badgr (OpenAI-Compatible Backend)

If you're already using the OpenAI API, you can also point your client at **AI Badgr**, which implements the same API surface (chat completions, streaming, JSON mode).

AI Badgr uses optimized open-source models to provide more affordable inference and also supports optional private/self-hosted modes for teams that need additional data control.

```bash
export OPENAI_API_KEY=YOUR_API_KEY
export OPENAI_BASE_URL=https://aibadgr.com/api/v1
```

**Python:**
```python
from openai import OpenAI
client = OpenAI(api_key="YOUR_API_KEY", base_url="https://aibadgr.com/api/v1")
response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role":"user","content":"Hello!"}], max_tokens=200)
print(response.choices[0].message.content)
```

**JavaScript:**
```javascript
import OpenAI from 'openai';
const client = new OpenAI({ apiKey: 'YOUR_API_KEY', baseURL: 'https://aibadgr.com/api/v1' });
const response = await client.chat.completions.create({ model: 'gpt-3.5-turbo', messages: [{ role: 'user', content: 'Hello!' }], max_tokens: 200 });
console.log(response.choices[0].message.content);
```


**cURL:**
```bash
curl https://aibadgr.com/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"Hello!"}],"max_tokens":200}'
```

**Notes:**
- Streaming: `"stream": true`
- JSON mode: `"response_format": {"type": "json_object"}`
- Because AI Badgr follows the OpenAI API spec, most existing OpenAI client code works by only changing the `base_url`.
