# 🧠 Footprints Bot — AI Admission Assistant

[🔗 Live Demo](https://footprints-bot.vercel.app/)  
Built using **LangChain**, **OpenAI GPT-4**, **FastAPI**, and **React**, Footprints Bot is an AI-powered assistant that helps parents explore preschool programs, ask questions, and schedule visits — all through natural multi-turn conversation.

---

## 🚀 Features

- 🤖 Conversational AI using LangChain Agents + OpenAI GPT
- 🔁 Multi-turn reasoning with context tracking
- 🧠 Intent classification for program, fee, visit, and safety queries
- 📍 Center recommendations via city and locality filtering
- 📚 FAQ routing through a structured knowledge base
- 🔐 API key protection via `.env` file
- 🗃 JSON-based data store (extensible to MongoDB)

---

## 🗂 Project Structure

```
footprints-chat/
├── backend/
│   ├── bot.py                # Core logic and prompt orchestration
│   ├── centers.json          # Data for all Footprints centers
│   ├── knowledge_base.py     # Structured FAQs
│   ├── .env                  # API key config
│   └── test.py               # Bot testing script
├── frontend/
│   ├── public/
│   └── src/                  # Basic UI (optional)
```

---

## ⚙️ Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/priyanshusinghal12/Footprints-Bot.git
cd footprints-chat/backend
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment

Create a `.env` file in the backend folder:

```env
OPENAI_API_KEY=your-openai-api-key-here
```

### 4. Run the Bot

```bash
python bot.py
```

---

## 💬 Sample Interaction

```
👤 Hi! I want to know about daycare programs.
🤖 Sure! We offer:
- Pre-School: 9 AM – 12 PM
- Full Day Care: 9 AM – 6:30 PM
- After School: 3:30 PM – 6:30 PM
All programs run Mon–Fri.
```

---

## 🌐 Deployment

- **Frontend**: Hosted on [Vercel](https://vercel.com/)
- **Backend API**: Hosted on [Render](https://render.com/)
- Optional Docker support for future deployment

---

## 🙌 Acknowledgements

- [OpenAI](https://platform.openai.com/)
- [LangChain](https://www.langchain.com/)
- [Vercel](https://vercel.com/)
- [Render](https://render.com/)

---

## 👨‍💻 Author

**Priyanshu Singhal**  
BSc Mathematics, University of Waterloo  
📫 psinghal@uwaterloo.ca · 🌐 [LinkedIn](https://www.linkedin.com/in/priyanshusinghal12/)
