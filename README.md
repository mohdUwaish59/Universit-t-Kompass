# 🎓 Universität Kompass

An AI-powered web application that recommends German university programs based on your resume. This tool helps students find the most suitable academic programs by analyzing their qualifications, experience, and skills.

## 🌟 Features

- **Resume Analysis**: Upload your resume in PDF format for AI-powered analysis
- **Smart Matching**: Uses advanced AI embeddings to match your profile with university programs
- **Detailed Information**: Provides comprehensive details about recommended programs including:
  - University name and program title
  - Program links and university portal links
  - Contact information
  - Application deadlines
- **User-Friendly Interface**: Built with Streamlit for an intuitive user experience

## 🛠️ Technical Stack

- **Frontend**: Streamlit
- **AI/ML**: 
  - OpenAI GPT-4 for resume analysis
  - FAISS for vector similarity search
  - LangChain for AI processing
- **Database**: MongoDB for storing university data
- **PDF Processing**: PyPDF2
- **Data Processing**: Pandas, NumPy

## 📋 Prerequisites

- Python 3.8 or higher
- MongoDB database
- OpenAI API key
- Required Python packages (listed in requirements.txt)

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Universitaet-Kompass.git
cd Universitaet-Kompass
```

2. Create and activate a virtual environment:
```bash
python -m venv kompas-env
source kompas-env/bin/activate  # On Windows: kompas-env\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following variables:
```
MONGO_URI=your_mongodb_connection_string
OPENAI_API_KEY=your_openai_api_key
```

## 💻 Usage

1. Start the Streamlit application:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to the provided local URL (typically http://localhost:8501)

3. Upload your resume in PDF format

4. Wait for the AI to analyze your resume and provide university program recommendations

## 📁 Project Structure

```
Universitaet-Kompass/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── data/                 # Data directory
│   ├── faiss_universities.pkl
│   └── merged_program_data.csv
├── utils/                # Utility functions
├── Scrape/              # Web scraping scripts
├── Vectorization/       # Vectorization scripts
└── .env                 # Environment variables (not tracked in git)
```

## 🔒 Environment Variables

The following environment variables need to be set:

- `MONGO_URI`: MongoDB connection string
- `OPENAI_API_KEY`: OpenAI API key

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⚠️ Disclaimer

This tool is still in development and some features may be improved in the future. The recommendations provided are based on a dataset of German universities and programs.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for providing the AI models
- Streamlit for the web framework
- FAISS for efficient similarity search
- MongoDB for database services 